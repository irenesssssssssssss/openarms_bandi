from datetime import date
import json
import sqlite3
import httpx
import pytest
from models import ScrapedGrant
from database.repository import Repository
from scrapers.base import BaseScraper
from scrapers.catalogue import content_text, deadline_from_text, ListingItem
from scrapers.eu_portal import EuPortalScraper
from scrapers.official_sources import UnipolisScraper, SardegnaScraper, OpenSocietyScraper
from services.eligibility import evaluate_eligibility
from services.relevance import score_grant
from services import refresh


def save(repo, g):
    r,e = score_grant(g), evaluate_eligibility(g)
    return repo.upsert_grant(g,r.score,r.level,r.reasons,r.category,e.status,e.reasons)


def test_iso_api_date():
    assert BaseScraper.parse_date('2026-11-05T00:00:00.000+0000') == date(2026,11,5)


def test_submission_not_project_expiration():
    html='<p>Pubblicato il 1 settembre 2026.</p><p>Domande fino alle ore 18 del <b>10 novembre 2026</b>.</p><p>Progetti in scadenza al <b>31 dicembre 2026</b>.</p>'
    assert deadline_from_text(content_text(html)) == date(2026,11,10)
    assert deadline_from_text('Pubblicato il 1 settembre 2026. Domande entro il 10 novembre.') is None


def test_sardegna_annual_call_year_not_deadline():
    s=SardegnaScraper()
    try:
        g=s.make_grant(ListingItem('Bando 2026','https://example.test/a.pdf'),'Domande dalle ore 9 del 29 ottobre alle ore 15 del 5 dicembre\n2025.')
        assert g.deadline == date(2025,12,5)
    finally:s.close()


def test_unipolis_public_json_endpoint():
    s=UnipolisScraper()
    try:
        s._robots_allowed=lambda url:(True,'test')
        def handler(req):
            assert req.method=='POST' and req.url.path.endswith('/filtra-bandi')
            assert json.loads(req.content)=={'chips':[],'year':'','toggle':False}
            return httpx.Response(200,json='<div class="card-bando"><h2 class="card-title-bando">Bando sociale</h2><a href="/site/bando/sociale/">Scopri</a></div>')
        s.client.close();s.client=httpx.Client(transport=httpx.MockTransport(handler))
        assert s.read_listings()[0].url.endswith('/site/bando/sociale/')
    finally:s.close()


def test_eu_multipart_query_filters_and_topic_mapping():
    s=EuPortalScraper()
    try:
        s._robots_allowed=lambda url:(True,'test')
        def handler(req):
            assert req.headers['content-type'].startswith('multipart/form-data')
            assert b'filename="query.json"' in req.content and b'"type": ["1"]' in req.content
            assert b'"language": "en"' in req.content
            return httpx.Response(200,json={'results':[],'totalResults':0})
        s.client.close();s.client=httpx.Client(transport=httpx.MockTransport(handler))
        assert s.search('CERV')['totalResults']==0
        assert s.parse_result({'metadata':{'type':['ORGANISATION']}}) is None
        g=s.parse_result({'summary':'Education for refugees','metadata':{'type':['1'],'language':['en'],'identifier':['CERV-2030-TEST'],'deadlineDate':['2030-11-05'],'status':['31094502']}})
        assert g.program=='CERV' and g.deadline==date(2030,11,5)
        assert evaluate_eligibility(g).status=='Da verificare'
    finally:s.close()


def test_osf_valid_empty_vs_access_error():
    s=OpenSocietyScraper()
    try:
        assert s.parse_listing('<h1 class="pageTitle">Grants and Fellowships</h1><a class="a-grantsCard" href="/grants/f"><span class="a-grantsCard__subtitle">Fellowship</span></a>',s.listing_urls[0])==[]
        with pytest.raises(ValueError):s.parse_listing('<p>Access denied</p>',s.listing_urls[0])
    finally:s.close()


def test_old_database_migration_and_closed_without_deadline(tmp_path):
    path=tmp_path/'old.sqlite3';repo=Repository(path)
    with sqlite3.connect(path) as c:
        c.execute('ALTER TABLE grants DROP COLUMN program');c.execute('ALTER TABLE grants DROP COLUMN source_closed')
    repo=Repository(path)
    g=ScrapedGrant('test','https://example.test/call','1','Human rights and refugee education',program='CERV',source_closed=True)
    save(repo,g);repo.mark_expired();row=repo.list_grants(True)[0]
    assert row['program']=='CERV' and row['expired']==1
    g.source_closed=None;save(repo,g)
    assert repo.list_grants(True)[0]['expired']==1


def test_source_failure_retains_cache_and_other_sources(tmp_path,monkeypatch):
    repo=Repository(tmp_path/'data.sqlite3');save(repo,ScrapedGrant('offline','https://example.test/old','old','Refugee education'))
    class Offline(BaseScraper):
        source_name='offline'
        def scrape(self,known_urls=None):raise RuntimeError('unavailable')
    class Healthy(BaseScraper):
        source_name='healthy'
        def scrape(self,known_urls=None):return [ScrapedGrant('healthy','https://example.test/new','new','Soccorso in mare')]
    monkeypatch.setattr(refresh,'SCRAPERS',[Offline,Healthy]);result=refresh.refresh_all(repo)
    assert result.status=='partial' and result.sources['offline']['status']=='ERRORE'
    assert result.sources['healthy']['items']==1 and len(repo.list_grants(True))==2


def test_english_relevance_and_financial_limits():
    g=ScrapedGrant('test','https://example.test/1','1','Human rights education for young refugees',eligible_entities='Organizzazioni non profit con entrate annue inferiori a 500.000 euro')
    assert score_grant(g).score>=50 and evaluate_eligibility(g).status=='Da verificare'
    assert score_grant(ScrapedGrant('test','https://example.test/2','2','Risarcimento danni')).score==0


def test_distinct_annual_editions_and_eu_topics_are_not_merged():
    from services.deduplication import duplicate_score
    old = {'title':'Avviso 2/2025','funder':'Ministero'}
    new = {'title':'Avviso 2/2026','funder':'Ministero'}
    assert duplicate_score(old,new)==0
    a = {'title':'Education for youth','funder':'Commissione','deadline':'2030-11-05','official_url':'https://ec.europa.eu/topic-details/CERV-A'}
    b = dict(a,official_url='https://ec.europa.eu/topic-details/CERV-B')
    assert duplicate_score(a,b)==0


def test_sardegna_opening_date_is_not_closing_date():
    s=SardegnaScraper()
    try:
        g=s.make_grant(ListingItem('Bando 2026','https://example.test/a.pdf'),
            'Domande a partire dalle ore 9 del 7 settembre 2026 e comunque non oltre le ore 15 del 30 settembre 2026.')
        assert g.deadline == date(2026,9,30)
    finally:s.close()


def test_truncated_news_excerpt_does_not_use_publication_date():
    text = 'La proposta deve essere presentata entro […]\nData: 30 Settembre 2026\nCondividi\nLa presentazione deve avvenire entro il termine perentorio del 12 gennaio 2027.'
    assert deadline_from_text(text) == date(2027,1,12)
