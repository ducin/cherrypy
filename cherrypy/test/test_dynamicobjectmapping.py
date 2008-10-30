from cherrypy.test import test
from cherrypy._cptree import Application
test.prefer_parent_path()

import cherrypy


script_names = ["", "/foo", "/users/fred/blog", "/corp/blog"]

def setup_server():
    class SubSubRoot:
        def index(self):
            return "SubSubRoot index"
        index.exposed = True

        def default(self, *args):
            return "SubSubRoot default"
        default.exposed = True

        def handler(self):
            return "SubSubRoot handler"
        handler.exposed = True

    subsubnodes = {
        '1': SubSubRoot(),
        '2': SubSubRoot(),
    }

    class SubRoot:
        def index(self):
            return "SubRoot index"
        index.exposed = True

        def default(self, *args):
            return "SubRoot %s" % (args,)
        default.exposed = True

        def handler(self):
            return "SubRoot handler"
        handler.exposed = True

        def getsubnode(self, objname):
            return subsubnodes.get(objname, None)

    subnodes = {
        '1': SubRoot(),
        '2': SubRoot(),
    }
    class Root:
        def index(self):
            return "index"
        index.exposed = True

        def default(self, *args):
            return "default %s" % (args,)
        default.exposed = True

        def handler(self):
            return "handler"
        handler.exposed = True

        def getsubnode(self, objname):
            return subnodes.get(objname)

    #--------------------------------------------------------------------------
    # DynamicNodeAndMethodDispatcher example.
    # This example exposes a fairly naive HTTP api
    class SomeModel(object):
        def __init__(self, id, name):
            self.id = id
            self.name = name

        def __unicode__(self):
            return unicode(self.name)

    model_lookup = {
        1: SomeModel(1, 'foo'),
        2: SomeModel(2, 'bar'),
    }

    def make_model(name, id=None):
        if not id:
            id = max(*model_lookup.keys()) + 1
        model_lookup[id] = SomeModel(id, name)
        return id

    class ObjectNode(object):
        exposed = True

        def POST(self, name):
            """
            Allow the creation of a new Object
            """
            return "POST %d" % make_model(name)

        def GET(self):
            return unicode(sorted(model_lookup.keys()))

        def getsubnode(self, objname):
            try:
                id = int(objname)
            except ValueError:
                return None
            return ModelInstanceNode(id)

    class ModelInstanceNode(object):
        exposed = True
        def __init__(self, id):
            self.id = id
            self.model = model_lookup.get(id, None)

            # For all but PUT methods there MUST be a valid user identified
            # by self.id
            if not self.model and cherrypy.request.method != 'PUT':
                raise cherrypy.HTTPError(404)

        def GET(self, *args, **kwargs):
            """
            Return the appropriate representation of the instance.
            """
            return unicode(self.model)

        def POST(self, name):
            """
            Update the fields of the user instance.
            """
            self.model.name = name
            return "POST %d" % self.model.id

        def PUT(self, name):
            """
            Create a new user with the specified id, or edit it if it already exists
            """
            if self.model:
                # Edit the current model
                self.model.name = name
                return "PUT %d" % self.model.id
            else:
                # Make a new model with said attributes.
                return "PUT %d" % make_model(name, self.id)

        def DELETE(self):
            """
            Delete the user specified at the id.
            """
            id = self.model.id
            del model_lookup[self.model.id]
            del self.model
            return "DELETE %d" % id


    Root.models = ObjectNode()

    d = cherrypy.dispatch.DynamicNodeDispatcher()
    md = cherrypy.dispatch.DynamicNodeAndMethodDispatcher()
    for url in script_names:
        conf = {'/': {
                    'request.dispatch': d,
                    'user': (url or "/").split("/")[-2]
                },
                '/models': {
                    'request.dispatch': md},
                }
        cherrypy.tree.mount(Root(), url, conf)

    cherrypy.config.update({'environment': "test_suite"})


from cherrypy.test import helper

class DynamicObjectMappingTest(helper.CPWebCase):

    def testObjectMapping(self):
        for url in script_names:
            prefix = self.script_name = url

            self.getPage('/')
            self.assertBody('index')

            self.getPage('/handler')
            self.assertBody('handler')

            # Dynamic dispatch will succeed here for the subnodes
            # so the subroot gets called
            self.getPage('/1/')
            self.assertBody('SubRoot index')

            self.getPage('/2/')
            self.assertBody('SubRoot index')

            self.getPage('/1/handler')
            self.assertBody('SubRoot handler')

            self.getPage('/2/handler')
            self.assertBody('SubRoot handler')

            # Dynamic dispatch will fail here for the subnodes
            # so the default gets called
            self.getPage('/asdf/')
            self.assertBody("default ('asdf',)")

            self.getPage('/asdf/asdf')
            self.assertBody("default ('asdf', 'asdf')")

            self.getPage('/asdf/handler')
            self.assertBody("default ('asdf', 'handler')")

            # Dynamic dispatch will succeed here for the subsubnodes
            # so the subsubroot gets called
            self.getPage('/1/1/')
            self.assertBody('SubSubRoot index')

            self.getPage('/2/2/')
            self.assertBody('SubSubRoot index')

            self.getPage('/1/1/handler')
            self.assertBody('SubSubRoot handler')

            self.getPage('/2/2/handler')
            self.assertBody('SubSubRoot handler')

            # Dynamic dispatch will fail here for the subsubnodes
            # so the SubRoot gets called
            self.getPage('/1/asdf/')
            self.assertBody("SubRoot ('asdf',)")

            self.getPage('/1/asdf/asdf')
            self.assertBody("SubRoot ('asdf', 'asdf')")

            self.getPage('/1/asdf/handler')
            self.assertBody("SubRoot ('asdf', 'handler')")

    def testMethodDispatch(self):
        # GET acts like a container
        self.getPage("/models")
        self.assertBody("[1, 2]")
        self.assertHeader('Allow', 'GET, HEAD, POST')

        # POST to the container URI allows creation
        self.getPage("/models", method="POST", body="name=baz")
        self.assertBody("POST 3")
        self.assertHeader('Allow', 'GET, HEAD, POST')

        # POST to a specific instanct URI results in a 404
        # as the resource does not exit.
        self.getPage("/models/5", method="POST", body="name=baz")
        self.assertStatus(404)

        # PUT to a specific instanct URI results in creation
        self.getPage("/models/5", method="PUT", body="name=boris")
        self.assertBody("PUT 5")
        self.assertHeader('Allow', 'DELETE, GET, HEAD, POST, PUT')

        # GET acts like a container
        self.getPage("/models")
        self.assertBody("[1, 2, 3, 5]")
        self.assertHeader('Allow', 'GET, HEAD, POST')

        test_cases = (
            (1, 'foo', 'fooupdated', 'DELETE, GET, HEAD, POST, PUT'),
            (2, 'bar', 'barupdated', 'DELETE, GET, HEAD, POST, PUT'),
            (3, 'baz', 'bazupdated', 'DELETE, GET, HEAD, POST, PUT'),
            (5, 'boris', 'borisupdated', 'DELETE, GET, HEAD, POST, PUT'),
        )
        for id, name, updatedname, headers in test_cases:
            self.getPage("/models/%d" % id)
            self.assertBody(name)
            self.assertHeader('Allow', headers)

            # Make sure POSTs update already existings resources
            self.getPage("/models/%d" % id, method='POST', body="name=%s" % updatedname)
            self.assertBody("POST %d" % id)
            self.assertHeader('Allow', headers)

            # Make sure PUTs Update already existing resources.
            self.getPage("/models/%d" % id, method='PUT', body="name=%s" % updatedname)
            self.assertBody("PUT %d" % id)
            self.assertHeader('Allow', headers)

            # Make sure DELETES Remove already existing resources.
            self.getPage("/models/%d" % id, method='DELETE')
            self.assertBody("DELETE %d" % id)
            self.assertHeader('Allow', headers)


        # GET acts like a container
        self.getPage("/models")
        self.assertBody("[]")
        self.assertHeader('Allow', 'GET, HEAD, POST')

if __name__ == "__main__":
    setup_server()
    helper.testmain()
