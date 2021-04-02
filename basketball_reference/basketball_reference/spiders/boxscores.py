# -*- coding: utf-8 -*-
import scrapy
from scrapy.linkextractors import LinkExtractor
from datetime import date
# from scrapy.spiders import CrawlSpider, Rule

import re

class BoxscoresSpider(scrapy.Spider):
    name = 'boxscores'
    allowed_domains = ['basketball-reference.com']
    start_urls = []

    def __init__(self, **kwargs):
        '''
        Expects seasons and months.
        '''
        if 'seasons' in kwargs:
            self.seasons = [int(x) for x in kwargs['seasons'].split(',')]
        else:
            self.seasons = []

        if 'from_season' and 'to_season' in kwargs:
            from_season = int(kwargs['from_season'])
            to_season = int(kwargs['to_season'])

            self.seasons = [x for x in range(from_season, to_season + 1)]

        if 'months' in kwargs:
            if kwargs['months'] == 'all':
                self.months = [x for x in range(12)]
            else:
                self.months = [int(x) - 1 for x in kwargs['months'].split(',')]
        else:
            if self.seasons:
                self.months = self.months = [x for x in range(12)]
            else:
                self.months = ()

        if 'date' in kwargs:
            if kwargs['date'] == 'today':
                self.seasons = [date.today().year - 1, date.today().year, date.today().year + 1]
                self.months = [date.today().month - 1]
            if kwargs['date'] == 'season':
                self.seasons = [date.today().year - 1, date.today().year, date.today().year + 1]
                self.months = [x for x in range(12)]

        if 'games' in kwargs:
            if self.seasons:
                self.games = ()
            else:
                self.games = [x for x in kwargs['games'].split(',')]
        else:
            self.games = ()

        if 'only-schedules' in kwargs:
            self.only_schedules = True
        else:
            self.only_schedules = False


    def start_requests(self):
        '''
        Initial requests that will be processed, based on the arguments passed.
        '''
        BASE_URL = 'https://www.basketball-reference.com'
        SCHEDULE_URL = '/leagues/NBA_{season}_games-{month}.html'
        MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 
                        'august', 'september', 'october', 'november', 'december']

        for season in self.seasons:
            for month in self.months:
                url = BASE_URL + SCHEDULE_URL.format(
                            season=season, month=MONTHS[month])
                yield scrapy.Request(url, callback=self.parse_schedule)
        
        for game_id in self.games:
            url = '{}/boxscores/{}.html'.format(BASE_URL, game_id)
            yield scrapy.Request(url, callback=self.parse_game)


    def parse_schedule(self, response):
        '''
        Extracts information about the schedule.
        '''
        if not self.only_schedules:
            for a in response.xpath('//a/@href'):
                url = a.extract()
                if re.match(r'/boxscores/(\d){9}([A-Z]){3}\.html', url):
                    yield response.follow(url, callback=self.parse_game)


        games_xpath = '//table[@id="schedule"]//tbody//tr[not(contains(@class, "thead"))]'
        games = response.xpath(games_xpath)

        season = re.search(r"/NBA_([0-9]{4})?_games-[a-z]*.html", response.url).group(1)
        month = re.search(r"/NBA_[0-9]{4}_games-([a-z]*)?.html", response.url).group(1)

        entries = []
        for game in games:
            entry = self.get_game_entry()

            entry["game_id"] = game.xpath('.//*[@data-stat="date_game"]//@csk').get()

            game_id = entry["game_id"] 
            y, m, d = int(game_id[0:4]), int(game_id[4:6]), int(game_id[6:8])
            entry["date"] = date(y, m, d).isoformat()
            
            entry["start_time"] = game.xpath('.//*[@data-stat="game_start_time"]//text()').get()
            entry["visitor_team"] = game.xpath('.//*[@data-stat="visitor_team_name"]//text()').get()
            entry["visitor_team_id"] = game.xpath('.//*[@data-stat="visitor_team_name"]//@csk').get()[:3]
            entry["visitor_pts"] = game.xpath('.//*[@data-stat="visitor_pts"]//text()').get()
            entry["home_team"] = game.xpath('.//*[@data-stat="home_team_name"]//text()').get()
            entry["home_team_id"] = game.xpath('.//*[@data-stat="home_team_name"]//@csk').get()[:3]
            entry["home_pts"] = game.xpath('.//*[@data-stat="home_pts"]//text()').get()
            entry["overtimes"] = game.xpath('.//*[@data-stat="overtimes"]//text()').get()
            entry["attendance"] = game.xpath('.//*[@data-stat="attendance"]//text()').get()
            entry["game_remarks"] = game.xpath('.//*[@data-stat="game_remarks"]//text()').get()

            entries.append(entry)

        if entries:
            yield { 'file_name': '{}_{}'.format(season, month), 
                    'type': 'schedule', 
                    'dir': 'schedule/games', 
                    'data': entries, 
                    'fieldnames': self.get_game_keys() }
            
    def parse_game(self, response):
        game_id = re.search(r"/([\dA-Z]*)?.html", response.url).group(1)

        basic_entries = []
        advanced_entries = []

        boxscores = response.xpath('//table[starts-with(@id, "box-")]')
        for bs in boxscores:
            html_id = bs.attrib['id']
            team_id = re.search('box-([A-Z]{3}?)-.*-.*', html_id).group(1)
            box_type = re.search('box-[A-Z]{3}-(.*-.*)?', html_id).group(1)

            # player extract
            players = bs.xpath('tbody//tr[not(contains(@class, "thead"))]')
            for index, player in enumerate(players):
                pnum = index + 1
                
                if box_type == 'game-advanced':
                    entry = self.get_advanced_entry()
                else:
                    entry = self.get_basic_entry()

                entry["game_id"] = game_id
                entry["team_id"] = team_id
                entry["box_type"] = box_type
                
                y, m, d = int(game_id[0:4]), int(game_id[4:6]), int(game_id[6:8])
                entry["date"] = date(y, m, d).isoformat()

                if re.search(team_id, game_id):
                    entry["ishome"] = True
                else:
                    entry["ishome"] = False

                stats = player.xpath('th | td')
                for stat in stats:
                    dt_st = stat.attrib['data-stat']
                    entry["pnum"] = pnum

                    if stat.xpath('a'):   # if it has link...
                        entry[dt_st] = stat.xpath('a/text()').get()
                        entry['{}_href'.format(dt_st)] = stat.xpath('a/@href').get()
                    else:
                        entry[dt_st] = stat.xpath('text()').get()

                    if 'csk' in stat.attrib:
                        if dt_st == "mp":
                            entry['sp'] = stat.attrib['csk']
                        else:
                            entry['{}_csk'.format(dt_st)] = stat.attrib['csk']

                    if 'data-append-csv' in stat.attrib:
                        entry['{}_id'.format(dt_st)] = stat.attrib['data-append-csv']
                pass # end stats for

                if entry['box_type'] == 'game-advanced':
                    advanced_entries.append(entry)
                else:
                    basic_entries.append(entry)
                
            pass # end player for
        
        if advanced_entries:
            yield { 'file_name': game_id[4:], 
                    'type': 'boxscore', 
                    'dir': 'games/boxscores/advanced/{}'.format(game_id[:4]), 
                    'data': advanced_entries,
                    'fieldnames': self.get_advanced_keys() }
        
        if basic_entries:
            yield { 'file_name': game_id[4:], 
                    'type': 'boxscore', 
                    'dir': 'games/boxscores/basic/{}'.format(game_id[:4]), 
                    'data': basic_entries, 
                    'fieldnames': self.get_basic_keys() }


    
    def get_basic_keys(self):
        keys = [
            "game_id",
            "team_id",
            "box_type",
            "date", 
            "ishome",
            "pnum",
            "player",
            "player_href",
            "player_csk",
            "player_id",
            "mp",
            "sp",
            "fg",
            "fga",
            "fg_pct",
            "fg3",
            "fg3a",
            "fg3_pct",
            "ft",
            "fta",
            "ft_pct",
            "orb",
            "drb",
            "trb",
            "ast",
            "stl",
            "blk",
            "tov",
            "pf",
            "pts",
            "plus_minus",
            "reason",
        ]
        return keys

    def get_advanced_keys(self):
        keys = ["game_id", 
            "team_id", 
            "box_type", 
            "date",  
            "ishome", 
            "pnum", 
            "player", 
            "player_href", 
            "player_csk", 
            "player_id", 
            "mp",
            "sp",
            "ts_pct", 
            "efg_pct", 
            "fg3a_per_fga_pct", 
            "fta_per_fga_pct", 
            "orb_pct", 
            "drb_pct", 
            "trb_pct", 
            "ast_pct", 
            "stl_pct", 
            "blk_pct", 
            "tov_pct", 
            "usg_pct", 
            "off_rtg", 
            "def_rtg", 
            "bpm", 
            "reason"]
        return keys    
        
    def get_basic_entry(self):
        entry = {}
        keys = self.get_basic_keys()
        for key in keys:
            if key in ['sp', 'mp']:
                entry[key] = 0
            else:
                entry[key] = None
        return entry

    def get_advanced_entry(self):
        entry = {}
        keys = self.get_advanced_keys()
        for key in keys:
            if key in ['sp', 'mp']:
                entry[key] = 0
            else:
                entry[key] = None
        return entry

    def get_game_keys(self):
        keys = [
            "game_id",
            "date",
            "start_time",
            "visitor_team",
            "visitor_team_id",
            "visitor_pts",
            "home_team",
            "home_team_id",
            "home_pts",
            "overtimes",
            "attendance",
            "game_remarks"
        ]
        return keys

    def get_game_entry(self):
        entry = {}
        keys = self.get_game_keys()

        for key in keys:
            entry[key] = None

        return entry
