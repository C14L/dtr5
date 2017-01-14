import toolbox
from django.test import SimpleTestCase

import toolbox_imgur


class ToolboxTestCase(SimpleTestCase):

    def test_sr_str_to_list(self):
        a = 'AskReddit, IamA , t:1990 ,Reddit.com dragonsfuckingcars'
        b = ['AskReddit', 'IamA', 't:1990', 'Reddit.com', 'dragonsfuckingcars']
        li = toolbox.sr_str_to_list(a)
        self.assertEqual(li, b)

    def test_set_imgur_url(self):
        orig = ('https://i.imgur.com/kMoI9Vn.jpg',
                'https://i.imgur.com/f7VXJQF',
                'https://imgur.com/S1dZBPm',
                'https://imgur.com/gallery/HFoOCeg',
                'http://redddate.com/static/nopic.jpg')

        mres = ('https://i.imgur.com/kMoI9Vnm.jpg',
                'https://i.imgur.com/f7VXJQFm.jpg',
                'https://i.imgur.com/S1dZBPmm.jpg',
                'https://i.imgur.com/HFoOCegm.jpg',
                'http://redddate.com/static/nopic.jpg')

        tres = ('https://i.imgur.com/kMoI9Vnt.jpg',
                'https://i.imgur.com/f7VXJQFt.jpg',
                'https://i.imgur.com/S1dZBPmt.jpg',
                'https://i.imgur.com/HFoOCegt.jpg',
                'http://redddate.com/static/nopic.jpg')

        for i in range(len(orig)):
            res = toolbox_imgur.set_imgur_url(orig[i], 'm')
            self.assertEqual(res, mres[i])
            res = toolbox_imgur.set_imgur_url(orig[i], 't')
            self.assertEqual(res, tres[i])
