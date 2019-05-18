class TC:
    def __init__(self):
        self.token = 'C57DB8'
        self.url_base = 'http://siri.nxtbus.act.gov.au:11000/'
        self.endpoints = ['sm', 'vm', 'pt', 'et']
        self.service_name = {
            'poll status': 'status.xml',
            'manage data subscription': 'subscription.xml',
            'poll data': 'polldata.xml',
            'report data ready': 'dataready.xml',
            'direct delivery': 'directdelivery.xml',
            'request for data': 'service.xml'
        }
