import warnings
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import datetime
import time
import random
from tmdbv3api import TMDb, Movie, TV
import multi_thread as m


warnings.filterwarnings('ignore')

# crawler headers
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36'}
# country dataframe
df_country = pd.read_excel('country.xlsx')


def replace_space(str_raw):
    str_raw = str_raw.replace("\t", "").replace("\n", "")
    return str_raw


def tmdb_init(language):
    """
    :param language: The language of the data being acquired through tmdb3 API .
    :return: Initialized API called tmdb.
    """
    def decorator(func):
        def wrapper(*arg):
            tmdb = TMDb()
            tmdb.api_key = 'd8fde0e756b1cc63645f793cfac7c15a'
            tmdb.language = language
            tmdb.debug = True
            return func(*arg)
        return wrapper
    return decorator


def new_rank_fetch(url: str):
    """
    :param url: The URL to FlixPatrol ranking information, in string format.
    :return: The scraping result on that website, a list of dictionary having each key correspond to each column of the result dataframe.
    """
    res = requests.get(url=url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    return_info = []
    if 'world' in url:
        mv_platforms = soup.select('div[id$="1"]')
        tv_platforms = soup.select('div[id$="2"]')
        for platform in mv_platforms:
            mv_titles = platform.select('a')[2:]
            return_info = return_info + [{'platform': platform.select_one('h2').text.split(' on')[1].strip(' '), 'film_type': 'mv',
                                          'date': url.split("/")[-1], 'country': 'world', 'film_rank': n+1,
                                          'film_title': replace_space(mv_titles[n].text),
                                          'film_par': mv_titles[n]["href"][7:]} for n in range(len(mv_titles))]
        for platform in tv_platforms:
            tv_titles = platform.select('a')[2:]
            return_info = return_info + [{'platform': platform.select_one('h2').text.split(' on')[1].strip(' '), 'film_type': 'tv',
                                          'date': url.split("/")[-1], 'country': 'world', 'film_rank': n+1,
                                          'film_title': replace_space(tv_titles[n].text),
                                          'film_par': tv_titles[n]["href"][7:]} for n in range(len(tv_titles))]
    else:
        blocks = soup.select('div.content.mb-14')
        for block in blocks:
            platform = block.select_one('h2').text.split('TOP')[0]
            boards = block.select('div.w-3\/4')
            for board in boards:
                if 'Movie' in board.select_one('h3').text:
                    mv_titles = board.select('a')
                    return_info = return_info + [{'platform': platform.strip(' '), 'film_type': 'mv', 'date': url.split("/")[-1],
                                                  'country': url.split("/")[-2], 'film_rank': n+1,
                                                  'film_title': replace_space(mv_titles[n].text),
                                                  'film_par': mv_titles[n]["href"][7:]} for n in range(len(mv_titles))]
                elif 'TV' in board.select_one('h3').text:
                    tv_titles = board.select('a')
                    return_info = return_info + [{'platform': platform.strip(' '), 'film_type': 'tv', 'date': url.split("/")[-1],
                                                  'country': url.split("/")[-2], 'film_rank': n+1,
                                                  'film_title': replace_space(tv_titles[n].text),
                                                  'film_par': tv_titles[n]["href"][7:]} for n in range(len(tv_titles))]
                else:
                    pass
    return return_info


def flixpatrol_fetch(parameter: str):
    """
    :param parameter: The parameter of the film, in string format.
    :return: A dictionary with each key corresponds to the columns of result dataframe.
    """
    url = "https://flixpatrol.com/title/" + parameter
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    # film_par and film_title
    film_info = {'film_par': parameter}
    try:
        film_info['film_title'] = replace_space(soup.select_one('h1.mb-3').text)
    except AttributeError:
        return film_info
    # ????????????
    try:
        info = soup.select_one('div.card.-mx-content').select("div.card-body")
        for block in info:
            if 'STARRING' in block.text:
                soup_crews = block.text.split('\n')
                for people in soup_crews:
                    # ????????????/??????
                    if people == "STARRING":
                        film_info['film_starring'] = soup_crews[soup_crews.index('STARRING') + 1]
                    elif people == 'DIRECTED BY':
                        film_info['film_director'] = soup_crews[soup_crews.index('DIRECTED BY') + 1]
                    else:
                        pass
            else:
                film_info['summary'] = replace_space(block.text)
    except AttributeError:
        pass
    # ??????????????????
    genre_ch = {'Drama': '??????', 'Adventure': '??????', 'Comedy': '??????', 'Science Fiction': '??????', 'Animated': '??????',
                'Horror': '??????', 'Music': '??????', 'Thriller': '??????', 'Biopic': '??????', 'Action': '??????', 'Romance': '??????',
                'Crime': '??????', 'Superhero': '????????????', 'Documentary': '??????', 'History': '??????', 'War': '??????',
                'Fantasy': '??????', 'Animation': '??????', 'Reality-Show': '?????????', 'Quiz Show': '????????????', 'Mystery': '??????',
                'Fairy Tale': '??????', 'Talk Show': '?????????', 'Western': '??????'}

    soup_info = replace_space(soup.select_one('div.flex.flex-wrap.text-sm.leading-6.text-gray-500').text)
    soup_info = soup_info.split("|")
    if soup_info[0] == 'Movie':
        film_info['film_type'] = 'mv'
    elif soup_info[0] == 'TV Show':
        film_info['film_type'] = 'tv'
    else:
        pass
    soup_info.pop(0)
    # ??????
    try:
        film_info['series'] = soup.select_one('div.flex.flex-wrap.text-sm.leading-6.text-gray-500').select_one('a').text
        soup_info.pop(-1)
    except AttributeError:
        pass
    tags = []
    for info in soup_info:
        # ????????????
        if '/' in info:
            film_info['film_date'] = info
        # ????????????
        elif info in list(genre_ch.keys()):
            film_info['film_genre'] = genre_ch[info]
        # ????????????
        elif info in df_country['country'].tolist():
            film_info['film_country'] = info
        else:
            tags.append(info)
    # ????????????
    film_info['film_tag'] = ','.join(tags)
    # IMDB??????
    film_info['imdb'] = replace_space(soup.select('div.mb-1.text-2xl.text-gray-400')[0].text)
    # ???????????????
    film_info['rottentomatoes'] = replace_space(soup.select('div.mb-1.text-2xl.text-gray-400')[1].text)
    return film_info


@tmdb_init('en')
def tmdb_match_mv(film: dict):
    """
    :param film: The dictionary of film information, which is the result of flixpatrol_fetch.
    :return: A dictionary of matched film on TMDb, with keys of 'film_type', 'film_par' and 'id'.
    """
    movie = Movie()
    results = movie.search(film['film_title'])
    # condition_1: if the "release date" is matched
    try:
        # could happen ValueError when the value is NaN, in this case jump to condition_2
        fp_date = datetime.datetime.strptime(film['film_date'], '%m/%d/%Y').strftime('%Y-%m-%d')
        # create a dict for dates of tmdb results
        tmdb_dates = {}
        for result in results:
            tmdb_dates[getattr(result, 'release_date', np.nan)] = result.id
        # compare each date in the dict with fp_date, if pair successfully then return
        if fp_date in list(tmdb_dates.keys()):
            print('--Found result with matched date--')
            return {'film_type': 'mv', 'film_par': film['film_par'], 'id': tmdb_dates[fp_date]}
        # else raise Value Error and continue condition_2
        else:
            raise ValueError
    # condition_2: if the "casts" or "director" are matched
    except ValueError:
        # could happen AttributeError when the value is NaN, in this case choose the first search result
        #    because these kinds of films either usually have few similar movie name or don't have matched result
        try:
            fp_crews = [name.strip(' ') for name in film['film_starring'].split(',')] + \
                       [name.strip(' ') for name in film['film_director'].split(',')]
        except AttributeError:
            return {'film_type': 'mv', 'film_par': film['film_par'], 'id': results[0].id}
        for result in results:
            detail = movie.details(result.id)
            tmdb_crews = [crew.name for crew in detail.casts.crew if crew.job == 'Director'] + \
                         [cast.name for cast in detail.casts.cast]
            # return when the crews are not disjoint
            if not set(fp_crews).isdisjoint(set(tmdb_crews)):
                print('--Found result with matched crews--')
                return {'film_type': 'mv', 'film_par': film['film_par'], 'id': result.id}
            else:
                pass


@tmdb_init('en')
def tmdb_match_tv(film: dict):
    """
    :param film: The dictionary of film information, which is the result of flixpatrol_fetch.
    :return: A dictionary of matched film on TMDb, with keys of 'film_type', 'film_par' and 'id'.
    """
    tv = TV()
    results = tv.search(film['film_title'])
    # condition_1: if the "release date" is matched
    try:
        # could happen ValueError when the value is NaN, in this case jump to condition_2
        fp_date = datetime.datetime.strptime(film['film_date'], '%m/%d/%Y').strftime('%Y-%m-%d')
        # create a dict for dates of tmdb results
        tmdb_dates = {}
        for result in results:
            tmdb_dates[getattr(result, 'first_air_date', np.nan)] = result.id
        # compare each date in the dict with fp_date, if pair successfully then return
        if fp_date in list(tmdb_dates.keys()):
            print('--Found result with matched date--')
            return {'film_type': 'tv', 'film_par': film['film_par'], 'id': tmdb_dates[fp_date]}
        # else raise Value Error and continue condition_2
        else:
            raise ValueError
    except ValueError:
        # condition_2: if the "casts" or "director" are matched
        try:
            fp_crews = [name.strip(' ') for name in film['film_starring'].split(',')] + \
                       [name.strip(' ') for name in film['film_director'].split(',')]
        except AttributeError:
            return {'film_type': 'tv', 'film_par': film['film_par'], 'id': results[0].id}
        for result in results:
            detail = tv.details(result.id)
            tmdb_crews = [crew.name for crew in detail.credits.crew if crew.job == 'Director'] + \
                         [cast.name for cast in detail.credits.cast]
            # return when the crews are not disjoint
            if not set(fp_crews).isdisjoint(set(tmdb_crews)):
                print('--Found result with matched crews--')
                return {'film_type': 'tv', 'film_par': film['film_par'], 'id': result.id}
            else:
                pass


@tmdb_init('zh-TW')
def tmdb_fetch_mv(film_info: dict):
    """
    :param film_info: A dictionary with key 'id', indicating the TMDb id of a film. It should be the return dictionary of tmdb_match_mv.
    :return: A dictionary of all the detailed information of that film.
    """
    movie = Movie()
    detail = movie.details(film_info['id'])
    # release_date
    film_info['release_date'] = detail.release_date
    # zh_title
    film_info['zh_title'] = detail.title
    # film_country
    try:
        film_info['film_country_iso'] = detail.production_countries[0]['iso_3166_1']
    except IndexError:
        pass
    # film_countries_list
    film_info['film_countries_list'] = ','.join([country['iso_3166_1'] for country in detail.production_countries])
    # collection
    film_info['collection'] = getattr(detail.belongs_to_collection, 'name', np.nan)
    # directors
    film_info['directors'] = ','.join([crew.name for crew in detail.casts.crew if crew.job == 'Director'])
    # casts
    film_info['casts'] = ','.join([cast.name for cast in detail.casts.cast])
    # production_companies
    film_info['production_companies'] = ','.join([pc.name for pc in detail.production_companies])
    # overview(zh-TW)
    film_info['zh_overview'] = detail.overview
    # overview(en)
    film_info['en_overview'] = ''.join([version.data.overview for version in detail.translations['translations'] if version['iso_639_1'] == 'en'])
    # genres
    film_genre_code = {'28': "??????", '12': "??????", '16': "??????", '35': "??????", '80': "??????",
                       '99': "??????", '18': "??????", '10751': "??????", '14': "??????", '36': "??????",
                       '27': "??????", '10402': "??????", '9648': "??????", '10749': "??????", '878': "??????",
                       '10770': "??????", '53': "??????", '10752': "??????", '37': "??????",
                       '10759': "????????????", '10762': "??????", '10763': "??????", '10765': "???????????????",
                       '10764': "?????????", '10767': "?????????", '10766': "?????????", '10768': "???????????????"}
    film_info['genre_list'] = ','.join([film_genre_code[str(genre.id)] for genre in detail.genres])
    # keywords
    film_info['keyword_list'] = ','.join([keyword.name for keyword in detail.keywords.keywords])
    return film_info


@tmdb_init('zh-TW')
def tmdb_fetch_tv(film_info: dict):
    """
    :param film_info: A dictionary with key 'id', indicating the TMDb id of a film. It should be the return dictionary of tmdb_match_tv.
    :return: A dictionary of all the detailed information of that film.
    """
    tv = TV()
    detail = tv.details(film_info['id'])
    # first_air_date
    film_info['release_date'] = detail.first_air_date
    # zh_title
    film_info['zh_title'] = detail.name
    # film_country: ???????????????????????????(???getattr?????????)
    try:
        film_info['film_country_iso'] = detail.origin_country[0]
    except IndexError:
        pass
    # directors
    film_info['directors'] = ','.join([crew.name for crew in detail.credits['crew'] if crew.job == 'Director'])
    # casts
    film_info['casts'] = ','.join([cast.name for cast in detail.credits['cast']])
    # production_companies
    film_info['production_companies'] = ','.join([pc.name for pc in detail.production_companies])
    # overview(zh-TW)
    film_info['zh_overview'] = detail.overview
    # overview(en)
    film_info['en_overview'] = ''.join([version.data.overview for version in detail.translations['translations'] if version['iso_639_1'] == 'en'])
    # genres
    film_genre_code = {'28': "??????", '12': "??????", '16': "??????", '35': "??????", '80': "??????",
                       '99': "??????", '18': "??????", '10751': "??????", '14': "??????", '36': "??????",
                       '27': "??????", '10402': "??????", '9648': "??????", '10749': "??????", '878': "??????",
                       '10770': "??????", '53': "??????", '10752': "??????", '37': "??????",
                       '10759': "????????????", '10762': "??????", '10763': "??????", '10765': "???????????????",
                       '10764': "?????????", '10767': "?????????", '10766': "?????????", '10768': "???????????????"}
    film_info['genre_list'] = ','.join([film_genre_code[str(genre.id)] for genre in detail.genres])
    # keywords
    url = 'https://www.themoviedb.org/tv/'
    res = requests.get(url=url + str(id), headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    film_info['keyword_list'] = ','.join([keyword.text for keyword in soup.select('section.keywords.right_column li')])
    return film_info


def pipeline_1(areadates_url: list):
    """
    :param areadates_url: A list of all the FlixPatrol Rank url to scrape.
    :return: A dataframe of rank info.
    """
    # fetch rank info
    print('=' * 100, '\n', '*****Crawling Rank*****')
    rank_info = []
    for i, url in enumerate(areadates_url):
        try:
            print("?????????????????????", url)
            rank_info = rank_info + new_rank_fetch(url)
        except requests.exceptions.ConnectionError:
            print('!!!Connection end!!!')
            time.sleep(5)
            rank_info = rank_info + new_rank_fetch(url)
        print('?????????{}/{}'.format(i + 1, len(areadates_url)))
        time.sleep(random.randrange(3))
    df_rank = pd.DataFrame(rank_info)
    print("*****Rank Crawling Completed*****")
    return df_rank


def pipeline_2(film_parameter_list: list):
    """
    :param film_parameter_list: A list of film_par. They are used to scrape the film info on FlixPatrol website.
    :return: A dataframe of flixpatrol info.
    """
    print('=' * 100, '\n', '*****Crawling FlixPatrol Information*****')
    flixpatrol_info = []
    for i, par in enumerate(film_parameter_list):
        try:
            print('?????????????????????', par)
            flixpatrol_info.append(flixpatrol_fetch(par))
        except requests.exceptions.ConnectionError:
            print('!!!Connection end!!!')
            time.sleep(5)
            flixpatrol_info.append(flixpatrol_fetch(par))
        print('?????????{}/{}'.format(i + 1, len(film_parameter_list)))
        time.sleep(random.randrange(3))
    print("*****FlixPatrol Info Crawling Completed*****")
    df_flixpatrol = pd.DataFrame(flixpatrol_info)
    return df_flixpatrol


def pipeline_3(fp_info_list: list):
    """
    :param fp_info_list: The result of FlixPatrol Dataframe, in the format of dictionaries within list.
    :return: A dataframe of TMDb info
    """
    print('=' * 100, '\n', '*****Fetching TMDb Information*****')
    tmdb_info = []
    for i, film in enumerate(fp_info_list):
        try:
            if film['film_type'] == 'mv':
                print('????????????: [MV]', film['film_par'])
                tmdb_info.append(tmdb_fetch_mv(tmdb_match_mv(film)))
            else:
                print('????????????: [TV]', film['film_par'])
                tmdb_info.append(tmdb_fetch_tv(tmdb_match_tv(film)))
            print('?????????{}/{}'.format(i+1, len(fp_info_list)))
        except (IndexError, TypeError):
            print("????????????! [film_title]:{}, [film_date]:{}".format(film['film_title'], film['film_date']))
    print("*****TMDb Info Fetching Completed*****")
    df_tmdb = pd.DataFrame(tmdb_info)
    return df_tmdb


if __name__ == '__main__':
    a = 0










