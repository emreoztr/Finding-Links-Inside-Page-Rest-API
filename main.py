import json
from logging import exception
from mimetypes import init
from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
import time

class CommonAnalysisTools:
    @staticmethod
    def create_req_session(max_redirections=3):
        session = requests.Session()
        session.max_redirects = max_redirections
        return session
class URLAnalysis:
    class ExternalLinkAnalysis:
        def __init__(self, url):
            self.parsedUrl=url
            session = CommonAnalysisTools.create_req_session()
            self.page = None
            t0=time.time()
            try:
                self.page = session.get(self.parsedUrl, timeout=3)
            except requests.exceptions.Timeout as ex:
                self.responseCode = 310
                self.responseMessage='Timeout'
            except requests.exceptions.TooManyRedirects as ex:
                self.responseCode = 310
                self.responseMessage='Too Many Redirects'
            except requests.exceptions.ConnectionError as ex:
                self.responseCode = 404
                self.responseMessage="Not Found"
            except requests.exceptions.InvalidSchema as ex:
                self.responseCode = 400
                self.responseMessage='Bad Request'
            except:
                self.responseCode = 999
                self.responseMessage='Invalid Content Type'  
            
            if self.page != None:
                
                self.finalUrl=self.page.url
                self.responseCode = self.page.status_code
                self.responseMessage=self.page.reason
                self.redirectedURLs=[page.url for page in self.page.history]
            else:
                self.redirectedURLs=[]
                self.finalUrl=self.parsedUrl
            passedTime = int((time.time() - t0) * 1000)

            self.secured = self.check_security()
            
            self.reachable=self.check_reachable_status()
            
            self.totalAccessDuration=passedTime
            

        def check_security(self):
            return self.finalUrl[:5] == 'https'

        def check_reachable_status(self):
            return self.responseCode == 200

        
            
        def toJSON(self):
            return {"parsedUrl": self.parsedUrl,
                    "finalUrl": self.finalUrl,
                    "secured": self.secured,
                    "reachable": self.reachable,
                    "totalAccessDuration": self.totalAccessDuration,
                    "responseCode": self.responseCode,
                    "responseMessage": self.responseMessage
                    }

    #Inherited externallinkanalysis class
    class InternalLinkAnalysis(ExternalLinkAnalysis):
        def __init__(self, url):
            super().__init__(url)
            
            if self.reachable:
                self.contentLength=self.find_content_length(BeautifulSoup(self.page.text, 'html.parser'))
            else:
                self.contentLength = -1

        def find_content_length(self, html):
            return len(html.get_text())
            
        def toJSON(self):
            json_file = super().toJSON()
            json_file["redirectedURLs"] = self.redirectedURLs
            if self.reachable:
                json_file["contentLength"] = self.contentLength
            return json_file

    def __init__(self, url):
        self.url=url
        session = CommonAnalysisTools.create_req_session()
        t0 = time.time()
        page = session.get(self.url)
        self.responseCode = page.status_code
        htmlContent = BeautifulSoup(page.text, 'html.parser')
        self.internalLinks, self.externalLinks = self.find_inner_internal_external_links(htmlContent)
        self.internalLinks = [self.InternalLinkAnalysis(internalUrl).toJSON() for internalUrl in self.internalLinks]
        self.externalLinks = [self.ExternalLinkAnalysis(externalUrl).toJSON() for externalUrl in self.externalLinks]
        self.analysisDuration=-1
        self.redirectedURLs=page.history
        self.responseMessage=page.reason
        page.close()
        passed_time = int((time.time() - t0) * 1000)
        self.analysisDuration = passed_time

    def find_inner_internal_external_links(self, html):
        foundInternalLinks = []
        foundExternalLinks = []
        linkClasses = html.find_all('a')

        for linkClass in linkClasses:
            extendedLink = linkClass.get('href')
            if self.is_internal_link(extendedLink):
                foundInternalLinks.append(extendedLink)
            else:
                foundExternalLinks.append(extendedLink)
        
        return foundInternalLinks, foundExternalLinks
    
    def is_internal_link(self, link):
        linkDomain = self.__find_link_domain(link)
        mainUrlDomain = self.__find_link_domain(self.url)
        return linkDomain == mainUrlDomain
    
    def __find_link_domain(self, link):
        print(link)
        splittedLink = link.split('//')
        if len(splittedLink) <= 1:
            return False
        
        domain = splittedLink[1].split('/')[0]
        return domain

    def toJSON(self):
        return {"url": self.url,
                "analysisDuration": self.analysisDuration,
                "redirectedURLs": self.redirectedURLs,
                "responseCode": self.responseCode,
                "responseMessage": self.responseMessage,
                "internalLinks": self.internalLinks,
                "externalLinks": self.externalLinks}


app = FastAPI()


@app.get("/")
async def crawl_url(url: str = ''):
    return URLAnalysis(url).toJSON()
