############
### Author: Kenneth Miller
### Email Address: ken@erdosmiller.com
### Date: Wed Sep  9 21:02:54 2009
### Function: Basecamp API Wrapper!
############

import pdb
import base64
import urllib2
import httplib
import datetime
import re
from elementtree.ElementTree import fromstring, tostring
import elementtree.ElementTree as ET

from config import *

ALL = 'all'
PENDING = 'pending'
FINISHED = 'finished'

tdls_status = [ALL,PENDING,FINISHED]

tdl_status_lookup = {'all':ALL,
              'pending':PENDING,
              'finished':FINISHED,
              ALL:'all',
              PENDING:'pending',
              FINISHED:'finished',
}

#this is where we define the entire API! In a dict!
#this is where we define all READ methods
url_mapping = {'get_projects':'/projects.xml', #projects
               'get_project':'/projects/%d.xml',
               'who_am_i':'/me.xml', #people
               'all_people':'/people.xml',
               'people_in_project':'/projects/%d/people.xml',
               'people_in_company':'/companies/%d/people.xml',
               'get_person':'/people/%d.xml',
               'companies':'/companies.xml', #companies
               'get_companies_in_project':'/projects/%d/companies.xml',
               'get_company':'/companies/%d.xml',
               'get_categories':'/projects/%d/categories.xml', #categories #this is not complete
               'get_category':'/categories/%d.xml',
               'get_messages':'/projects/%d/posts.xml', #messages
               'get_message':'/posts/%d.xml',
               'get_message_by_category':'/projects/%d/cat/%d/posts.xml',
               'get_archived_messages':'/projects/%d/posts/archive.xml',
               'get_archived_messages_by_category':'/projects/%d/cat/%d/posts/archive.xml',
               'new_message':'/projects/%d/posts/new.xml',
               'edit_message':'/posts/%d/edit.xml',
               #'get_project_time':'/projects/%d/time_entries.xml', #required special implementation
               #TIME ENTRIES
               'get_all_todo_entries':'/todo_items/%d/time_entries.xml',
               #TODO Lists
               'get_entry':'/time_entries/%d.xml',
               'get_all_lists':'/projects/%d/todo_lists.xml?filter=%s',
               'get_list':'/todo_lists/%d.xml',
               #ToDo List Items
               'get_all_items':'/todo_lists/%d/todo_items.xml',
               'new_item':'/todo_lists/%d/todo_items/new.xml',
               'get_todo_item':'/todo_items/%d.xml'
               }

class pythonic_objectify(object):
    def __init__(self,tree,parent=None):
        
        self._parent = parent
        
        if isinstance(tree,str):
            self._tree = fromstring(tree)
        else:
            self._tree = tree

        #this is required to call on all the children
        self._children = [pythonic_objectify(child,self) for child in self._tree]
        
        #assigning attributes to the parent
        if parent is not None:
            
            #making the tags more pythonic - don't hate me!
            tag = self._tree.tag
            tag = tag.replace('-','_')

            #getting the tags value
            value = self._tree.text
            #known type conversion
            if 'type' in self._tree.attrib and value is not None:
                kind = self._tree.attrib['type']
                if kind == 'integer':
                    value = int(value)
                elif kind == 'float':
                    value = float(value)
                elif kind == 'boolean':
                    if value == 'false':
                        value = False
                    elif value == 'true':
                        value = True
                    else:
                        raise ValueError("I don't know how to handle this!")
                elif kind == 'date':
                    year, month, day = value.split('-')
                    value = datetime.datetime(int(year),int(month),int(day))
                
            #apply it to it's parent
            setattr(self._parent,tag,value)
        
    def __repr__(self):
        return '<%s>' % self._tree.tag

    def tostring(self):
        return tostring(self._tree)

    def __len__(self):
        return len(self._children)

    def __iter__(self):
        return self._children.__iter__()

    def __getitem__(self,index):
        try:
            return self._children[index]
        except AttributeError:
            return getattr(self,index)

    def get_children(self):
        return self._children
    
    def __iter__(self):
        return self._children.__iter__()
        

    children = property(get_children)
    data = property(get_children)
        
        
        

class Basecamp(object):    
    def __init__(self, baseURL, username, password):
        """Basic setup."""
        self.baseURL = baseURL
        if self.baseURL[-1] == '/':
            self.baseURL = self.baseURL[:-1]

        self.opener = urllib2.build_opener()

        self.auth_string = '%s:%s' % (username, password)
        self.encoded_auth_string = base64.encodestring(self.auth_string)

        self.encoded_auth_string = self.encoded_auth_string.replace('\n', '')
        self.headers = [
            ('Content-Type', 'application/xml'),
            ('Accept', 'application/xml'),
            ('Authorization', 'Basic %s' % self.encoded_auth_string), ]
        
        self.opener.addheaders = self.headers

    def _request(self, path, data=None):
        """Make an http request."""
        
        #what is this line for?
        if hasattr(data, 'findall'):
            data = ET.tostring(data)


        logger.debug('Requesting URL: %s ' % (self.baseURL + path, ) )

        req = urllib2.Request(url=self.baseURL + path, data=data)

        req.add_header('Content-Type', 'application/xml') 
        req.add_header('Accept', 'application/xml') 
        req.add_header('Authorization', 'Basic %s' % self.encoded_auth_string)
        
        response = self.opener.open(req)
        
        return response
    
    def __getattr__(self,index):
        if index in url_mapping.keys():
            def temp_func(*args):
                #print self._request(url_mapping[index] % args)
                return pythonic_objectify(self._request(url_mapping[index] % args).read())
                
            return temp_func
        else:
            return self.__dict__[index]

    def people_id_map(self,company_id=None):
        """Return a dictionary for everyone in BaseCamp."""
        keys = {}
        
        if company_id is None:
            people = self.all_people()
        else:
            people = self.people_in_company(company_id)

        for person in people:
            keys[person.id] = person.first_name + ' ' + person.last_name
        
        return keys
    
    def project_id_map(self):
        """Return a dictionary for all the projects in BaseCamp."""
        keys = {}
        for project in self.get_projects():
            keys[project.id] = project.name

        return keys

    def mark_todo_item_complete(self, item_id):   
        path = '/todo_items/%d/complete.xml' % item_id
        logger.debug("Marking todo item complete %s" % path)
        (headers, conn) = self._create_http_connection()
        conn.request( "PUT", path, "<todo-item />", headers)        
        res = conn.getresponse()
        logger.debug("Response code %d" % res.status)
        return res.status == 200
        
    def mark_todo_item_incomplete(self, item_id):        
        path = '/todo_items/%d/uncomplete.xml' % item_id        
        logger.debug("Marking todo item uncomplete %s" % path)
        (headers, conn) = self._create_http_connection()
        conn.request( "PUT", path, "<todo-item />", headers)        
        res = conn.getresponse()
        logger.debug("Response code %d" % res.status)
        return res.status == 200

    def update_todo_list(self, list_id, name, description ):
        path = '/todo_lists/%d.xml' % list_id
        logger.debug("Updating todo list %d - %s" % (list_id, name) )
        req = ET.Element('todo-list')
        ET.SubElement( req, "name").text = str( name )
        ET.SubElement( req, "description").text = str( description )
        
        (headers, conn) = self._create_http_connection()
        conn.request( "PUT", path, ET.tostring(req), headers )  
        res = conn.getresponse()
        logger.debug("Response code %d" % res.status)
        return res.status == 200        

    def update_todo_item(self, item_id, content):
        path = '/todo_items/%d.xml' % item_id
        logger.debug("Updateing todo item %d - %s" % (item_id, path) )
        req = ET.Element('todo-item')
        ET.SubElement( req, "content").text = str( content )
        (headers, conn) = self._create_http_connection()
        conn.request( "PUT", path, ET.tostring(req), headers )  
        res = conn.getresponse()
        logger.debug("Response code %d" % res.status)
        return res.status == 200

    def create_todo_list(self, project_id, list_name, list_description):
        path = '/projects/%d/todo_lists.xml' % project_id
                
        req = ET.Element('todo-list')
        
        ET.SubElement(req, 'description').text = str(list_description)
        ET.SubElement(req, 'name').text = str(list_name)
        
        
        response = self._request( path, req )
        logger.debug("Response code %d" % response.code)
        # logger.debug( response.read() )
        if response.code == 201:
            return int(response.headers['location'].split('/')[-1])
        else: 
            return False
    
    def delete_todo_list(self, list_id):
        path = '/todo_lists/%d.xml' % list_id
        logger.debug("Deleting todo list %s" % path)
        (headers, conn) = self._create_http_connection()
        conn.request( "DELETE", path, None, headers)        
        res = conn.getresponse()
        logger.debug("Delete status %d" % res.status)
        return res.status == 200
        
    def delete_todo_list_item(self, item_id):
        path = '/todo_items/%d.xml' % item_id
        (headers, conn) = self._create_http_connection()
        conn.request( "DELETE", path, None, headers)
        res = conn.getresponse()
        logger.debug("Delete status %d" % res.status)
        return res.status == 200
    
    def _create_http_connection( self ):
        m = re.search('([htps]+)://(.*)/*', self.baseURL)
        if m == None:
            return None
        prototocol = m.group(1)
        hostname = m.group(2)

        if prototocol.lower == "http":
            conn = httplib.HTTPConnection(hostname)
        else:
            conn = httplib.HTTPSConnection(hostname)

        headers_map = {}
        
        for header in self.headers:
            headers_map[header[0]] = header[1]
        return (headers_map, conn)
        
    
    def create_todo_item(self, list_id, content, party_id=None, notify=False):

        path = '/todo_lists/%d/todo_items.xml' % list_id
        
        req = ET.Element('todo-item')
        
        ET.SubElement(req, 'content').text = str(content)
        
        due = ET.SubElement(req, 'due-at')
        due.set('nil',str(True).lower())
        due.set('type','datetime')
        
        notify_elem = ET.SubElement(req,'notify')
        notify_elem.text = str(notify).lower()
        notify_elem.set('type','boolean')
        
        party = ET.SubElement(req,'responsible_party')
        
        if party_id is not None:
            ET.SubElement(req, 'responsible-party').text = str(party_id)
            ET.SubElement(req, 'notify').text = str(bool(notify)).lower()
        
        #print self._request(path,req)
        #pdb.set_trace()

        response = self._request(path,req)

        if response.code == 201:
            return int(response.headers['location'].split('/')[-1])
        else: 
            return False
        
        #return self.old_create_todo_item(list_id,content,party_id,notify)

    def get_project_time(self,project_id,page=1,return_all=True):
        """This method will return all time entries, if you'd like it to return the last 50 set return_all to false and select the page."""

        #print "Retrieving Page: %d" % page
        time_entries = []

        path = '/projects/%d/time_entries.xml?page=%d' % (project_id,page)
        
        req = urllib2.Request(url=self.baseURL + path, data=None)
        
        response = self.opener.open(req)
        
        data = response.read()

        objects = pythonic_objectify(data)
        
        pages = int(response.headers['x-pages'])
        page = int(response.headers['x-page'])

        time_entries.extend(objects.data)

        if page < pages:
            time_entries.extend(self.get_project_time(project_id,page+1,return_all))

        return time_entries
                                
                             
            
        
if __name__ == '__main__':
    
    import unittest
    
    from test_settings import *
    
    class APITests(unittest.TestCase):
        def setUp(self):
            self.conn = Basecamp(bc_url,bc_user,bc_pwd)

        def tearDown(self):
            pass

        def testGetCompany(self):
            company = self.conn.get_company(bc_primary_company_id)
            assert company.id == bc_primary_company_id

        def testGetProjects(self):
            projects = self.conn.get_projects()
            assert projects[0].id == bc_primary_project_id

        def testGetTDLS(self):
            tdls = self.conn.get_all_lists(bc_primary_project_id,ALL)

            assert bc_primary_tdl_id in [tdl.id for tdl in tdls]

        def testCreateToDoItem(self):
            new_id = self.conn.create_todo_item(bc_primary_tdl_id,'Test From python!')
            
            assert new_id > 0
            
        def testGetNewToDoListItem(self):
            t = self.conn.new_item(bc_primary_tdl_id)
        
    unittest.main()
