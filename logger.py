import logging
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',
                    encoding='utf-8', level=logging.INFO)
app_log = logging.getLogger(__name__)
