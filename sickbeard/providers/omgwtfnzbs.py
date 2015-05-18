# Author: Jordon Smith <smith@jordon.me.uk>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of SickGear.
#
# SickGear is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickGear is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickGear. If not, see <http://www.gnu.org/licenses/>.

import urllib
from datetime import datetime

import generic
import sickbeard
from sickbeard import tvcache, classes, logger, show_name_helpers
from sickbeard.exceptions import AuthException


try:
    import xml.etree.cElementTree as etree
except ImportError:
    import elementtree.ElementTree as etree

try:
    import json
except ImportError:
    from lib import simplejson as json


class OmgwtfnzbsProvider(generic.NZBProvider):
    def __init__(self):
        generic.NZBProvider.__init__(self, 'omgwtfnzbs', True, False)
        self.username = None
        self.api_key = None
        self.cache = OmgwtfnzbsCache(self)
        self.url = 'https://omgwtfnzbs.org/'

    def _checkAuth(self):

        if not self.username or not self.api_key:
            raise AuthException("Your authentication credentials for " + self.name + " are missing, check your config.")

        return True

    def _checkAuthFromData(self, parsed_data, is_XML=True):

        if parsed_data is None:
            return self._checkAuth()

        if is_XML:
            # provider doesn't return xml on error
            return True
        else:
            parsedJSON = parsed_data

            if 'notice' in parsedJSON:
                description_text = parsedJSON.get('notice')

                if 'information is incorrect' in parsedJSON.get('notice'):
                    logger.log(u"Incorrect authentication credentials for " + self.name + " : " + str(description_text),
                               logger.DEBUG)
                    raise AuthException(
                        "Your authentication credentials for " + self.name + " are incorrect, check your config.")

                elif '0 results matched your terms' in parsedJSON.get('notice'):
                    return True

                else:
                    logger.log(u"Unknown error given from " + self.name + " : " + str(description_text), logger.DEBUG)
                    return False

            return True

    def _get_season_search_strings(self, ep_obj):
        return [x for x in show_name_helpers.makeSceneSeasonSearchString(self.show, ep_obj)]

    def _get_episode_search_strings(self, ep_obj, add_string=''):
        return [x for x in show_name_helpers.makeSceneSearchString(self.show, ep_obj)]

    def _get_title_and_url(self, item):
        return (item['release'], item['getnzb'])

    def _doSearch(self, search, search_mode='eponly', epcount=0, retention=0):

        self._checkAuth()

        params = {'user': self.username,
                  'api': self.api_key,
                  'eng': 1,
                  'catid': '19,20',  # SD,HD
                  'retention': sickbeard.USENET_RETENTION,
                  'search': search}

        if retention or not params['retention']:
            params['retention'] = retention

        search_url = 'https://api.omgwtfnzbs.org/json/?' + urllib.urlencode(params)
        logger.log(u"Search url: " + search_url, logger.DEBUG)

        parsedJSON = self.getURL(search_url, json=True)
        if not parsedJSON:
            return []

        if self._checkAuthFromData(parsedJSON, is_XML=False):
            results = []

            for item in parsedJSON:
                if 'release' in item and 'getnzb' in item:
                    results.append(item)

            return results

        return []

    def findPropers(self, search_date=None):
        search_terms = ['.PROPER.', '.REPACK.']
        results = []

        for term in search_terms:
            for item in self._doSearch(term, retention=4):
                if 'usenetage' in item:

                    title, url = self._get_title_and_url(item)
                    try:
                        result_date = datetime.fromtimestamp(int(item['usenetage']))
                    except:
                        result_date = None

                    if result_date:
                        results.append(classes.Proper(title, url, result_date, self.show))

        return results


class OmgwtfnzbsCache(tvcache.TVCache):
    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)
        self.minTime = 20

    def _get_title_and_url(self, item):
        """
        Retrieves the title and URL data from the item XML node

        item: An elementtree.ElementTree element representing the <item> tag of the RSS feed

        Returns: A tuple containing two strings representing title and URL respectively
        """

        title = item.title if item.title else None
        if title:
            title = u'' + title
            title = title.replace(' ', '.')

        url = item.link if item.link else None
        if url:
            url = url.replace('&amp;', '&')

        return (title, url)

    def _getRSSData(self):
        params = {'user': provider.username,
                  'api': provider.api_key,
                  'eng': 1,
                  'catid': '19,20'}  # SD,HD

        rss_url = 'https://rss.omgwtfnzbs.org/rss-download.php?' + urllib.urlencode(params)

        logger.log(self.provider.name + u" cache update URL: " + rss_url, logger.DEBUG)

        data = self.getRSSFeed(rss_url)

        if data and 'entries' in data:
            return data.entries
        else:
            return []

provider = OmgwtfnzbsProvider()
