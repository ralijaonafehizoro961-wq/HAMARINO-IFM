from app.precision_search import queries,relevance_gate,published_from_url

def test_query_not_fixed():
    assert 'train' in ' '.join(queries('Un train relie Antananarivo à Toamasina'))
    assert 'russie' in ' '.join(queries('Madagascar et la Russie annoncent une coopération économique'))

def test_avoid_parliament_confusion():
    claim='Le président de Madagascar est allé en Russie pour le développement durable'
    passage='Le Président de l Assemblée nationale a voyagé en Russie. Madagascar coopération développement durable.'
    assert not relevance_gate(claim,passage)

def test_allow_related_without_every_keyword():
    assert relevance_gate('Madagascar Russie coopération économique', 'La Russie et Madagascar annoncent un accord économique bilatéral')

def test_not_match_one_keyword():
    assert not relevance_gate('Un train à grande vitesse relie Antananarivo à Toamasina','Le train a un nouveau programme culturel en ville.')

def test_url_month_not_day():
    assert published_from_url('https://www.lexpress.mg/2026/10/un-article.html')=='2026-10'
