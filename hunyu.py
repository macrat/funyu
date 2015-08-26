#!/usr/bin/python
#coding: utf-8

""" Blog writing markup language for BlankTar

		ふにゅう

					MIT License (c)2015 MacRat

>>> h = Hunyu()
>>> h.parse(''' title: test of hunyu
... author: MacRat
...
... hello!
... this is test.
... -- first section
... \\thello
... out of section
...
...
... -- inline items
... \\tthis is [[keyword]] text, and <<emphasis>> text.
... \\tinline {{code string}}.
...
... \\tmarkdown style [link text](/path/to/file).
... \\t[IMG: image](/path/to/img.png)
... ''')
>>> h.metadata['title']
'test of hunyu'
>>> h.metadata['author']
'MacRat'
>>> print(h.as_html())
<p>
hello!<br>
this is test.<br>
</p>
<section>
<h1>first section</h1>
<p>
hello<br>
</p>
</section>
<p>
out of section<br>
</p>
<section>
<h1>inline items</h1>
<p>
this is <strong>keyword</strong> text, and <em>emphasis</em> text.<br>
inline <code>code string</code>.<br>
</p>
<p>
markdown style <a href="/path/to/file">link text</a>.<br>
<a href="/path/to/img.png"><img src="/path/to/img.png" alt="image"></a><br>
</p>
</section>
<BLANKLINE>
"""


import sys
import datetime
import re
try:
	import urllib.parse as urlparse
except ImportError:
	import urlparse


if sys.version.startswith('2'):
	bytes = str
	str = unicode


class HunyuError(Exception):
	""" hunyu exception base """
	pass


class HunyuSyntaxError(HunyuError):
	""" incorrect hunyu syntax error """
	pass


class EndOfBlock(Exception):
	""" end of block element

	`remain` is line that not processed.
	if set this, parent block should process this string.
	"""

	def __init__(self, remain=None):
		self.remain = remain


def indent(string):
	""" indent string

	>>> indent('abc\\ndef\\n')
	'\\tabc\\n\\tdef\\n'
	"""

	return '\n'.join(
		'\t' + line if line else ''
		for line in string.split('\n')
	)


class Element:
	""" hunyu element base """

	def __init__(self):
		self.elements = []

	def as_hunyu(self):
		""" get as hunyu text
		Can't call it is.

		>>> Element().as_hunyu()
		Traceback (most recent call last):
			...
		NotImplementedError
		"""

		raise NotImplementedError()

	def as_html(self):
		""" get as HTML5
		Can't call it is.

		>>> Element().as_hunyu()
		Traceback (most recent call last):
			...
		NotImplementedError

		raise NotImplementedError()
		"""


class Block(Element):
	""" block element base """

	def __init__(self, level):
		assert isinstance(level, int)
		assert 1 <= level

		super().__init__()
		self.ended = False
		self.level = level

	def feed(self, line):
		""" append line """

		if len(self.elements) > 0 and not isinstance(self.elements[-1], Paragraph):
			try:
				self.elements[-1].feed(line)
			except EndOfBlock as e:
				if e.remain is None:
					return
			else:
				return

		if line.startswith('-- '):
			self.elements.append(Section(self.level + 1, line[len('-- '):].strip()))
		elif line.startswith('```'):
			type = line[len('``` '):].strip() or None
			self.elements.append(CodeBlock(type))
		elif line.startswith('p.s. '):
			date = datetime.datetime.strptime(
				line[len('p.s. '):].strip(),
				'%Y-%m-%d'
			).date()
			self.elements.append(PostScript(self.level + 1, date))
		elif line.strip() == '(((':
			self.elements.append(EmbeddedHTML())
		else:
			try:
				self.elements[-1].feed(line)
			except (EndOfBlock, IndexError):
				pass
			else:
				return

			if line.strip() != '':
				self.elements.append(Paragraph())
				self.elements[-1].feed(line)


class Hunyu(Block):
	""" hunyu parser

	`initial_level` -- top level H tag's number.

	>>> h = Hunyu()
	>>> h.feed('title: test')
	>>> h.feed('')
	>>> h.feed('this is test.')
	>>> h.feed('hello, world!')
	>>> h.as_hunyu()
	'title: test\\n\\nthis is test.\\nhello, world!\\n'
	>>> h.as_html()
	'<p>\\nthis is test.<br>\\nhello, world!<br>\\n</p>\\n'
	>>> h.metadata['title']
	'test'
	"""

	def __init__(self, initial_level=1):
		super().__init__(1)
		self.level = initial_level - 1
		self.metadata = MetaData()

	def feed(self, line):
		""" append line
		Line can't has line break

		>>> Hunyu().feed('can not include \\n.')
		Traceback (most recent call last):
			...
		ValueError: line argument can't include line break.
		"""

		if '\n' in line:
			raise ValueError("line argument can't include line break.")

		if self.metadata.ended is True:
			Block.feed(self, line)
		else:
			try:
				self.metadata.feed(line)
			except EndOfBlock:
				return

	def parse(self, string):
		""" parse multi line string """

		for line in string.splitlines():
			self.feed(line)

	def as_hunyu(self):
		return '{0}\n{1}'.format(
			self.metadata.as_hunyu(),
			''.join(elm.as_hunyu() for elm in self.elements)
		)

	def as_html(self):
		return ''.join(elm.as_html() for elm in self.elements)


class MetaData(Block, dict):
	""" metadata block
	First block in the hunyu document is metadata block.
	In this block, you can write metadata about document like a title or author.
	Metadata is key-value style. Key and value is separated by semicolon.

	>>> m = MetaData()
	>>> m.feed('key: value')
	>>> m.feed('abc:def')
	>>> m['key']
	'value'
	>>> m['abc']
	'def'

	>>> m.feed("hasn't semicolon is error")
	Traceback (most recent call last):
		...
	HunyuSyntaxError: metadata block expects key-value separated by semicolon.

	>>> m.feed(': no key is error')
	Traceback (most recent call last):
		...
	HunyuSyntaxError: key is required.

	>>> m.feed('')
	Traceback (most recent call last):
		...
	EndOfBlock
	>>> m.feed('after: end')
	Traceback (most recent call last):
		...
	EndOfBlock: after: end
	"""

	def __init__(self):
		super().__init__(1)

	def feed(self, line):
		assert isinstance(line, str)

		if self.ended:
			raise EndOfBlock(line)
		elif line.strip() == '':
			self.ended = True
			raise EndOfBlock()

		if ':' not in line:
			raise HunyuSyntaxError(
				'metadata block expects key-value separated by semicolon.'
			)

		items = line.split(':')
		key = items[0].strip()
		value = ':'.join(items[1:]).strip()

		if key == '':
			raise HunyuSyntaxError('key is required.')

		self[key] = value

	def as_hunyu(self):
		return '\n'.join('{0}: {1}'.format(key, self[key]) for key in self) + '\n'


class Paragraph(Block):
	""" paragraph block

	>>> p = Paragraph()
	>>> p.feed('hello, world!')
	>>> p.feed('this is test')
	>>> p.as_hunyu()
	'hello, world!\\nthis is test\\n'
	>>> p.as_html()
	'<p>\\nhello, world!<br>\\nthis is test<br>\\n</p>\\n'

	>>> p.feed('')
	Traceback (most recent call last):
		...
	EndOfBlock
	>>> p.feed('after end')
	Traceback (most recent call last):
		...
	EndOfBlock: after end
	"""

	def __init__(self):
		super().__init__(1)

	def feed(self, line):
		if line.strip() == '' or self.ended:
			self.ended = True
			raise EndOfBlock(line)
		else:
			self.elements.append(Line(line))

	def as_hunyu(self):
		return ''.join(line.as_hunyu() for line in self.elements)

	def as_html(self):
		return '<p>\n{0}</p>\n'.format(
			''.join(line.as_html() for line in self.elements)
		)


class Section(Block):
	""" section block

	>>> s = Section(2, 'test section')
	>>> s.feed('\\tthis is test')
	>>> s.as_hunyu()
	'-- test section\\n\\tthis is test\\n'
	>>> print(s.as_html())
	<section>
	<h2>test section</h2>
	<p>
	this is test<br>
	</p>
	</section>
	<BLANKLINE>

	>>> s.feed('')
	>>> s.feed('end of section')
	Traceback (most recent call last):
		...
	EndOfBlock: end of section
	>>> try:
	... 	s.feed('\\tafter end')
	... except EndOfBlock as e:
	... 	print(repr(e.remain))
	'\\tafter end'
	"""

	def __init__(self, level, title):
		assert isinstance(title, str)

		super().__init__(level)
		self.title = title

	def feed(self, line):
		if line.strip() != '' and not line.startswith('\t') or self.ended:
			self.ended = True
			raise EndOfBlock(line)
		else:
			Block.feed(self, line[1:])

	def as_hunyu(self):
		return '-- {0}\n{1}'.format(
			self.title,
			indent(''.join(elm.as_hunyu() for elm in self.elements))
		).replace('\n\t\n', '\n\n')

	def as_html(self):
		return '<section>\n<h{0}>{1}</h{0}>\n{2}</section>\n'.format(
			min(self.level, 6),
			self.title,
			''.join(elm.as_html() for elm in self.elements)
		)


class PostScript(Block):
	""" post script block

	>>> time = datetime.date(2015, 1, 1)
	>>> p = PostScript(1, time)
	>>> p.feed('\\thello, world')
	>>> p.feed('\\tthis is test')
	>>> p.as_hunyu()
	'p.s. 2015-01-01\\n\\thello, world\\n\\tthis is test\\n'
	>>> print(p.as_html())
	<ins>
	<b>p.s. <date>2015-01-01</date></b><br>
	<p>
	hello, world<br>
	this is test<br>
	</p>
	</ins>
	<BLANKLINE>

	>>> p.feed('')
	>>> p.feed('end of post script')
	Traceback (most recent call last):
		...
	EndOfBlock: end of post script
	>>> try:
	... 	p.feed('\\tafter end')
	... except EndOfBlock as e:
	... 	print(repr(e.remain))
	'\\tafter end'

	>>> h = Hunyu()
	>>> h.parse('''
	... p.s. 2015-04-01
	... \\tthis is test.
	... ''')
	>>> print(h.as_html())
	<ins>
	<b>p.s. <date>2015-04-01</date></b><br>
	<p>
	this is test.<br>
	</p>
	</ins>
	<BLANKLINE>
	"""

	def __init__(self, level, date):
		assert isinstance(date, datetime.date)

		super().__init__(level)
		self.date = date

	def feed(self, line):
		if line.strip() != '' and not line.startswith('\t') or self.ended:
			self.ended = True
			raise EndOfBlock(line)
		else:
			Block.feed(self, line[1:])

	def as_hunyu(self):
		return 'p.s. {0}\n{1}'.format(
			self.date.isoformat(),
			indent(''.join(elm.as_hunyu() for elm in self.elements))
		)

	def as_html(self):
		return '<ins>\n<b>p.s. <date>{0}</date></b><br>\n{1}</ins>\n'.format(
			self.date.isoformat(),
			''.join(x.as_html() for x in self.elements)
		)


class CodeBlock(Block):
	""" code block

	>>> c = CodeBlock('html')
	>>> c.feed('\\thello')
	>>> c.feed('\\tworld')
	>>> c.as_hunyu()
	'``` html\\n\\thello\\n\\tworld\\n```\\n'
	>>> c.as_html()
	'<pre class="code code_html">\\nhello\\nworld\\n</pre>\\n'

	>>> c = CodeBlock()
	>>> c.feed('\\ttest')
	>>> c.as_hunyu()
	'```\\n\\ttest\\n```\\n'
	>>> c.as_html()
	'<pre class="code">\\ntest\\n</pre>\\n'

	>>> c.feed("hasn't tab character is error.")
	Traceback (most recent call last):
		...
	HunyuSyntaxError: in code block, lines should be starts with tab character.

	>>> c.feed('```')
	Traceback (most recent call last):
		...
	EndOfBlock
	>>> try:
	... 	c.feed('\\tafter end')
	... except EndOfBlock as e:
	... 	print(repr(e.remain))
	'\\tafter end'

	>>> h = Hunyu()
	>>> h.parse('''
	... ``` html
	... \\tthis is <b>html</b> source code.
	... ```
	... ''')
	>>> print(h.as_html())
	<pre class="code code_html">
	this is &lt;b&gt;html&lt;/b&gt; source code.
	</pre>
	<BLANKLINE>
	"""

	def __init__(self, type=None):
		assert type is None or isinstance(type, str)

		super().__init__(1)
		self.type = type

	def feed(self, line):
		assert isinstance(line, str)

		if self.ended:
			raise EndOfBlock(line)
		elif line == '```':
			self.ended = True
			raise EndOfBlock()
		elif line != '' and not line.startswith('\t'):
			raise HunyuSyntaxError(
				'in code block, lines should be starts with tab character.'
			)
		else:
			line = line[1:]

			for rep in (('&', '&amp;'), ('<', '&lt;'), ('>', '&gt;')):
				line = line.replace(*rep)

			self.elements.append(line)

	def as_hunyu(self):
		if self.type is not None:
			type = ' ' + self.type
		else:
			type = ''

		content = indent('\n'.join(self.elements))

		return '```{0}\n{1}\n```\n'.format(type, content)

	def as_html(self):
		if self.type is not None:
			type = ' code_' + self.type
		else:
			type = ''

		content = '\n'.join(self.elements)

		return '<pre class="code{0}">\n{1}\n</pre>\n'.format(type, content)


class EmbeddedHTML(Block):
	""" embeded HTML block
	String that surrounded three brackets is "embedded html".
	In embedded html, all hunyu elements disregarded.
	If you wants use html tag like table or script, please use embedded html.

	>>> e = EmbeddedHTML()
	>>> e.feed('\\t<script>')
	>>> e.feed('\\talert("hello, [[world]]");')
	>>> e.feed('\\t</script>')
	>>> e.as_hunyu()
	'(((\\n\\t<script>\\n\\talert("hello, [[world]]");\\n\\t</script>\\n)))\\n'
	>>> e.as_html()
	'<script>\\nalert("hello, [[world]]");\\n</script>\\n'

	>>> e.feed("hasn't tab character is error.")
	Traceback (most recent call last):
		...
	HunyuSyntaxError: in embedded html, lines should be starts with tab character.

	>>> e.feed(')))')
	Traceback (most recent call last):
		...
	EndOfBlock
	>>> try:
	... 	e.feed('\\tafter end')
	... except EndOfBlock as e:
	... 	print(repr(e.remain))
	'\\tafter end'

	>>> h = Hunyu()
	>>> h.parse('''
	... (((
	... \\tthis is embedded html.
	... \\tcan include <b>html</b> tags.
	... )))
	... ''')
	>>> print(h.as_html())
	this is embedded html.
	can include <b>html</b> tags.
	<BLANKLINE>
	"""

	def __init__(self):
		super().__init__(1)

	def feed(self, line):
		assert isinstance(line, str)

		if self.ended:
			raise EndOfBlock(line)
		elif line.startswith(')))'):
			self.ended = True
			raise EndOfBlock()
		elif line != '' and not line.startswith('\t'):
			raise HunyuSyntaxError(
				'in embedded html, lines should be starts with tab character.'
			)
		else:
			self.elements.append(line[1:])

	def as_hunyu(self):
		return '(((\n{0}\n)))\n'.format(indent('\n'.join(self.elements)))

	def as_html(self):
		return '{0}\n'.format('\n'.join(self.elements))


class String(Element):
	""" string base

	>>> p = String('this is test')
	>>> p.as_hunyu()
	'this is test'
	>>> p.as_html()
	'this is test'
	"""

	splitter = re.compile(
		'\[\[(?P<keyword>.*)\]\]'
		'|'
		'<<(?P<emphasis>.*)>>'
		'|'
		'{{(?P<code>.*)}}'
		'|'
		'\[(?P<linktype>IMG:|)(?P<linktext>.*)\]\((?P<linkuri>.*)\)'
	)

	def __init__(self, string):
		assert isinstance(string, str)

		super().__init__()

		done = 0
		for match in self.splitter.finditer(string):
			self.elements.append(string[done:match.start()])
			done = match.end()

			if match.group('keyword') is not None:
				self.elements.append(Keyword(match.group('keyword')))
			elif match.group('emphasis') is not None:
				self.elements.append(Emphasis(match.group('emphasis')))
			elif match.group('code') is not None:
				self.elements.append(Code(match.group('code')))
			elif match.group('linktype') is not None:
				if match.group('linktype') == 'IMG:':
					link = ImageLink
				else:
					link = Link

				self.elements.append(link(
					match.group('linktext').strip(),
					match.group('linkuri').strip())
				)

		self.elements.append(string[done:])

	def as_hunyu(self):
		return ''.join(
			elm.as_hunyu() if isinstance(elm, Element) else elm
			for elm in self.elements
		)

	def as_html(self):
		return ''.join(
			elm.as_html() if isinstance(elm, Element) else elm
			for elm in self.elements
		)


class Line(String):
	""" one line string

	>>> l = Line('this is test')
	>>> l.as_hunyu()
	'this is test\\n'
	>>> l.as_html()
	'this is test<br>\\n'
	"""

	def as_hunyu(self):
		return '{0}\n'.format(super().as_hunyu())

	def as_html(self):
		return '{0}<br>\n'.format(super().as_html())


class Keyword(String):
	""" keyword element

	>>> k = Keyword('this is test')
	>>> k.as_hunyu()
	'[[this is test]]'
	>>> k.as_html()
	'<strong>this is test</strong>'
	"""

	def as_hunyu(self):
		return '[[{0}]]'.format(super().as_hunyu())

	def as_html(self):
		return '<strong>{0}</strong>'.format(super().as_html())


class Emphasis(String):
	""" emphasis element

	>>> e = Emphasis('this is test')
	>>> e.as_hunyu()
	'<<this is test>>'
	>>> e.as_html()
	'<em>this is test</em>'
	"""

	def as_hunyu(self):
		return '<<{0}>>'.format(super().as_hunyu())

	def as_html(self):
		return '<em>{0}</em>'.format(super().as_html())


class Code(String):
	""" inline code element

	>>> c = Code('this is test')
	>>> c.as_hunyu()
	'{{this is test}}'
	>>> c.as_html()
	'<code>this is test</code>'
	"""

	def __init__(self, text):
		super().__init__('')
		self.text = text

	def as_hunyu(self):
		return '{{{{{0}}}}}'.format(self.text)

	def as_html(self):
		return '<code>{0}</code>'.format(self.text)


class Link(String):
	""" link element

	>>> l = Link('test', './test.html')
	>>> l.as_hunyu()
	'[test](./test.html)'
	>>> l.as_html()
	'<a href="./test.html">test</a>'

	>>> l = Link('blog', 'http://blanktar.jp/blog/')
	>>> l.as_hunyu()
	'[blog](http://blanktar.jp/blog/)'
	>>> l.as_html()
	'<a href="http://blanktar.jp/blog/" target="_blank">blog</a>'
	"""

	def __init__(self, text, uri):
		super().__init__(text)
		self.uri = uri

	def as_hunyu(self):
		return '[{0}]({1})'.format(super().as_hunyu(), self.uri)

	def as_html(self):
		if urlparse.urlparse(self.uri).scheme:
			return '<a href="{0}" target="_blank">{1}</a>'.format(
				self.uri,
				super().as_hunyu()
			)
		else:
			return '<a href="{0}">{1}</a>'.format(self.uri, super().as_hunyu())


class ImageLink(Link):
	""" image link element

	>>> l = ImageLink('test', 'test.png')
	>>> l.as_hunyu() == '[IMG: test](test.png)'
	True
	>>> l.as_html() == '<a href="test.png"><img src="test.png" alt="test"></a>'
	True

	>>> l = ImageLink('test', 'http://blanktar.jp/test.png')
	>>> l.as_hunyu() == '[IMG: test](http://blanktar.jp/test.png)'
	True
	>>> l.as_html() == (
	... 	'<a href="http://blanktar.jp/test.png" target="_blank">'
	... 	'<img src="http://blanktar.jp/test.png" alt="test">'
	... 	'</a>'
	... )
	True
	"""

	def __init__(self, alt, uri):
		super().__init__('', uri)
		self.alt = alt

	def as_hunyu(self):
		return '[IMG: {0}]({1})'.format(self.alt, self.uri)

	def as_html(self):
		if urlparse.urlparse(self.uri).scheme:
			fmt = '<a href="{0}" target="_blank"><img src="{0}" alt="{1}"></a>'
		else:
			fmt = '<a href="{0}"><img src="{0}" alt="{1}"></a>'

		return fmt.format(self.uri, self.alt)


if __name__ == '__main__':
	import doctest
	doctest.testmod()
