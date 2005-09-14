<?xml version='1.0'?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:fo="http://www.w3.org/1999/XSL/Format"
                version='1.0'>
  <xsl:include href="html.xsl"/>
  <xsl:param name="generate.toc">
     book      toc
     appendix  toc
     section   toc
     refentry  toc
  </xsl:param>
  <xsl:param name="base.dir" select="''"/>
  <xsl:param name="use.id.as.filename" select="1"/>
</xsl:stylesheet>