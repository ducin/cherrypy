import test
test.prefer_parent_path()

import cherrypy
europoundUnicode = u'\x80\xa3'

class Root:
    def index(self, param):
        assert param == europoundUnicode
        yield europoundUnicode
    index.exposed = True
    
    def mao_zedong(self):
        return u"\u6bdb\u6cfd\u4e1c: Sing, Little Birdie?"
    mao_zedong.exposed = True

cherrypy.root = Root()
cherrypy.config.update({
        'server.log_to_screen': False,
        'server.environment': 'production',
        'encoding_filter.on': True,
        'decoding_filter.on': True
})


import helper


class DecodingEncodingFilterTest(helper.CPWebCase):
    
    def testDecodingEncodingFilter(self):
        europoundUtf8 = europoundUnicode.encode('utf-8')
        self.getPage('/?param=%s' % europoundUtf8)
        self.assertBody(europoundUtf8)
        
        # Default encoding should be utf-8
        self.getPage('/mao_zedong')
        self.assertBody("\xe6\xaf\x9b\xe6\xb3\xbd\xe4\xb8\x9c: "
                        "Sing, Little Birdie?")
        
        # Ask for utf-16.
        sing16 = ('\xff\xfe\xdbk\xfdl\x1cN:\x00 \x00S\x00i\x00n\x00g\x00,\x00 '
                  '\x00L\x00i\x00t\x00t\x00l\x00e\x00 '
                  '\x00B\x00i\x00r\x00d\x00i\x00e\x00?\x00')
        self.getPage('/mao_zedong', [('Accept-Charset', 'utf-16')])
        self.assertBody(sing16)
        
        # Ask for multiple encodings. ISO-8859-1 should fail, and utf-16
        # should be produced.
        self.getPage('/mao_zedong', [('Accept-Charset',
                                      'iso-8859-1;q=1, utf-16;q=0.5')])
        self.assertBody(sing16)
        
        # The "*" value should default to our default_encoding, utf-8
        self.getPage('/mao_zedong', [('Accept-Charset', '*;q=1, utf-7;q=.2')])
        self.assertBody("\xe6\xaf\x9b\xe6\xb3\xbd\xe4\xb8\x9c: "
                        "Sing, Little Birdie?")
        
        # Only allow iso-8859-1, which should fail and raise 406.
        self.getPage('/mao_zedong', [('Accept-Charset', 'iso-8859-1, *;q=0')])
        self.assertStatus("406 Not Acceptable")
        self.assertErrorPage(406)


if __name__ == "__main__":
    helper.testmain()