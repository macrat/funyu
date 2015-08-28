#!/usr/bin/python
# coding: utf-8

""" Blog writing markup language for BlankTar

		ふにゅう

					MIT License (c)2015 MacRat

>>> h = Funyu()
>>> h.parse(''' title: test of funyu
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
'test of funyu'
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


if sys.version.startswith('3'):
	unicode = str


class FunyuError(Exception):
	""" funyu exception base """
	pass


class FunyuSyntaxError(FunyuError):
	""" incorrect funyu syntax error

	>>> e = FunyuSyntaxError('test exception')
	>>> print(str(e))
	test exception
	>>> e.line_number = 5
	>>> print(str(e))
	line 5: test exception
	"""

	def __init__(self, message):
		self.message = message
		self.line_number = None

	def __str__(self):
		if self.line_number is not None:
			return 'line {0}: {1}'.format(self.line_number, self.message)
		else:
			return self.message


class EndOfBlock(Exception):
	""" end of block element

	`remain` is line that not processed.
	if set this, parent block should process this string.
	"""

	def __init__(self, remain=None):
		self.remain = remain

	def __str__(self):
		if self.remain:
			return self.remain
		else:
			return ''


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
	""" funyu element base """

	def __init__(self):
		self.elements = []

	def as_funyu(self):
		""" get as funyu text
		Can't call it is.

		>>> Element().as_funyu()
		Traceback (most recent call last):
			...
		NotImplementedError
		"""

		raise NotImplementedError()

	def as_html(self):
		""" get as HTML5
		Can't call it is.

		>>> Element().as_html()
		Traceback (most recent call last):
			...
		NotImplementedError
		"""

		raise NotImplementedError()


class Block(Element):
	""" block element base """

	def __init__(self, level):
		assert isinstance(level, int)
		assert 1 <= level

		Element.__init__(self)
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


class Funyu(Block):
	""" funyu parser

	`initial_level` -- top level H tag's number.

	>>> h = Funyu()
	>>> h.feed('title: test')
	>>> h.feed('')
	>>> h.feed('this is test.')
	>>> h.feed('hello, world!')
	>>> h.as_funyu()
	'title: test\\n\\nthis is test.\\nhello, world!\\n'
	>>> h.as_html()
	'<p>\\nthis is test.<br>\\nhello, world!<br>\\n</p>\\n'
	>>> h.metadata['title']
	'test'

	>>> h = Funyu()
	>>> h.feed(':invalid syntax')
	Traceback (most recent call last):
		...
	FunyuSyntaxError: line 1: key is required.
	"""

	def __init__(self, initial_level=1):
		Block.__init__(self, 1)
		self.level = initial_level - 1
		self.metadata = MetaData()
		self.line_number = 0

	def feed(self, line):
		""" append line
		Line can't has line break

		>>> Funyu().feed('can not include \\n.')
		Traceback (most recent call last):
			...
		ValueError: line argument can't include line break.
		"""

		self.line_number += 1

		if '\n' in line:
			raise ValueError("line argument can't include line break.")

		try:
			if self.metadata.ended is True:
				Block.feed(self, line)
			else:
				try:
					self.metadata.feed(line)
				except EndOfBlock:
					return
		except FunyuSyntaxError as e:
			e.line_number = self.line_number
			e.line_string = line
			raise e

	def parse(self, string):
		""" parse multi line string """

		for line in string.splitlines():
			self.feed(line)

	def as_funyu(self):
		return '{0}\n{1}'.format(
			self.metadata.as_funyu(),
			''.join(elm.as_funyu() for elm in self.elements)
		)

	def as_html(self):
		return ''.join(elm.as_html() for elm in self.elements)


class MetaData(Block, dict):
	""" metadata block
	First block in the funyu document is metadata block.
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
	FunyuSyntaxError: metadata block expects key-value separated by semicolon.

	>>> m.feed(': no key is error')
	Traceback (most recent call last):
		...
	FunyuSyntaxError: key is required.

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
		Block.__init__(self, 1)

	def feed(self, line):
		assert isinstance(line, (str, unicode))

		if self.ended:
			raise EndOfBlock(line)
		elif line.strip() == '':
			self.ended = True
			raise EndOfBlock()

		if ':' not in line:
			raise FunyuSyntaxError(
				'metadata block expects key-value separated by semicolon.'
			)

		items = line.split(':')
		key = items[0].strip()
		value = ':'.join(items[1:]).strip()

		if key == '':
			raise FunyuSyntaxError('key is required.')

		self[key] = value

	def as_funyu(self):
		return '\n'.join('{0}: {1}'.format(key, self[key]) for key in self) + '\n'


class Paragraph(Block):
	""" paragraph block

	>>> p = Paragraph()
	>>> p.feed('hello, world!')
	>>> p.feed('this is test')
	>>> p.as_funyu()
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
		Block.__init__(self, 1)

	def feed(self, line):
		if line.strip() == '' or self.ended:
			self.ended = True
			raise EndOfBlock(line)
		else:
			self.elements.append(Line(line))

	def as_funyu(self):
		return ''.join(line.as_funyu() for line in self.elements)

	def as_html(self):
		return '<p>\n{0}</p>\n'.format(
			''.join(line.as_html() for line in self.elements)
		)


class Section(Block):
	""" section block

	>>> s = Section(2, 'test section')
	>>> s.feed('\\tthis is test')
	>>> s.as_funyu()
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
		assert isinstance(title, (str, unicode))

		Block.__init__(self, level)
		self.title = title

	def feed(self, line):
		if line.strip() != '' and not line.startswith('\t') or self.ended:
			self.ended = True
			raise EndOfBlock(line)
		else:
			Block.feed(self, line[1:])

	def as_funyu(self):
		return '-- {0}\n{1}'.format(
			self.title,
			indent(''.join(elm.as_funyu() for elm in self.elements))
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
	>>> p.as_funyu()
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

	>>> h = Funyu()
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

		Block.__init__(self, level)
		self.date = date

	def feed(self, line):
		if line.strip() != '' and not line.startswith('\t') or self.ended:
			self.ended = True
			raise EndOfBlock(line)
		else:
			Block.feed(self, line[1:])

	def as_funyu(self):
		return 'p.s. {0}\n{1}'.format(
			self.date.isoformat(),
			indent(''.join(elm.as_funyu() for elm in self.elements))
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
	>>> c.as_funyu()
	'``` html\\n\\thello\\n\\tworld\\n```\\n'
	>>> c.as_html()
	'<pre class="code code_html">\\nhello\\nworld\\n</pre>\\n'

	>>> c = CodeBlock()
	>>> c.feed('\\ttest')
	>>> c.as_funyu()
	'```\\n\\ttest\\n```\\n'
	>>> c.as_html()
	'<pre class="code">\\ntest\\n</pre>\\n'

	>>> c.feed("hasn't tab character is error.")
	Traceback (most recent call last):
		...
	FunyuSyntaxError: in code block, lines should be starts with tab character.

	>>> c.feed('```')
	Traceback (most recent call last):
		...
	EndOfBlock
	>>> try:
	... 	c.feed('\\tafter end')
	... except EndOfBlock as e:
	... 	print(repr(e.remain))
	'\\tafter end'

	>>> h = Funyu()
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
		assert type is None or isinstance(type, (str, unicode))

		Block.__init__(self, 1)
		self.type = type

	def feed(self, line):
		assert isinstance(line, (str, unicode))

		if self.ended:
			raise EndOfBlock(line)
		elif line == '```':
			self.ended = True
			raise EndOfBlock()
		elif line != '' and not line.startswith('\t'):
			raise FunyuSyntaxError(
				'in code block, lines should be starts with tab character.'
			)
		else:
			line = line[1:]

			for rep in (('&', '&amp;'), ('<', '&lt;'), ('>', '&gt;')):
				line = line.replace(*rep)

			self.elements.append(line)

	def as_funyu(self):
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
	In embedded html, all funyu elements disregarded.
	If you wants use html tag like table or script, please use embedded html.

	>>> e = EmbeddedHTML()
	>>> e.feed('\\t<script>')
	>>> e.feed('\\talert("hello, [[world]]");')
	>>> e.feed('\\t</script>')
	>>> e.as_funyu()
	'(((\\n\\t<script>\\n\\talert("hello, [[world]]");\\n\\t</script>\\n)))\\n'
	>>> e.as_html()
	'<script>\\nalert("hello, [[world]]");\\n</script>\\n'

	>>> e.feed("hasn't tab character is error.")
	Traceback (most recent call last):
		...
	FunyuSyntaxError: in embedded html, lines should be starts with tab character.

	>>> e.feed(')))')
	Traceback (most recent call last):
		...
	EndOfBlock
	>>> try:
	... 	e.feed('\\tafter end')
	... except EndOfBlock as e:
	... 	print(repr(e.remain))
	'\\tafter end'

	>>> h = Funyu()
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
		Block.__init__(self, 1)

	def feed(self, line):
		assert isinstance(line, (str, unicode))

		if self.ended:
			raise EndOfBlock(line)
		elif line.startswith(')))'):
			self.ended = True
			raise EndOfBlock()
		elif line != '' and not line.startswith('\t'):
			raise FunyuSyntaxError(
				'in embedded html, lines should be starts with tab character.'
			)
		else:
			self.elements.append(line[1:])

	def as_funyu(self):
		return '(((\n{0}\n)))\n'.format(indent('\n'.join(self.elements)))

	def as_html(self):
		return '{0}\n'.format('\n'.join(self.elements))


class String(Element):
	""" string base

	>>> p = String('<<[[this]] <<is>> [[test]]>>')
	>>> p.as_funyu()
	'<<[[this]] <<is>> [[test]]>>'
	>>> p.as_html()
	'<em><strong>this</strong> <em>is</em> <strong>test</strong></em>'

	>>> p = String('[[[this]] is [[link]]](test)')
	>>> p.as_html()
	'<a href="test"><strong>this</strong> is <strong>link</strong></a>'

	>>> String('[[opend')
	Traceback (most recent call last):
		...
	FunyuSyntaxError: inline element is required close bracket.

	>>> String('[link in [link](uri)](uri)')
	Traceback (most recent call last):
		...
	FunyuSyntaxError: link element can't including link.
	"""

	link = re.compile(
		'\[(?P<linktype>IMG:|)(?P<linktext>.*)\]\((?P<linkuri>.*)\)'
	)

	def __init__(self, string):
		assert isinstance(string, (str, unicode))

		def findClose(string, start, end):
			level = 0
			for i in range(len(string)):
				if string[i:].startswith(start):
					level += 1
				elif string[i:].startswith(end):
					level -= 1

				if level == -1:
					return i

			raise FunyuSyntaxError('inline element is required close bracket.')

		def procStr(string):
			i = 0
			last = 0
			while i < len(string):
				key = string[i:i + 2]

				if key in ('[[', '<<', '{{'):
					self.elements.append(string[last:i])

					i += 2

					if key == '[[':
						end = i + findClose(string[i:], '[[', ']]')
						self.elements.append(Keyword(string[i:end]))
					elif key == '<<':
						end = i + findClose(string[i:], '<<', '>>')
						self.elements.append(Emphasis(string[i:end]))
					elif key == '{{':
						end = i + findClose(string[i:], '{{', '}}')
						self.elements.append(Code(string[i:end]))

					i = end + 2
					last = i

				i += 1

			remain = string[last:]
			if remain:
				self.elements.append(remain)

		Element.__init__(self)

		done = 0
		for match in self.link.finditer(string):
			procStr(string[done:match.start()])
			done = match.end()

			if match.group('linktype') == 'IMG:':
				link = ImageLink
			else:
				link = Link

			if self.link.search(match.group('linktext')):
				raise FunyuSyntaxError("link element can't including link.")

			self.elements.append(link(
				match.group('linktext').strip(),
				match.group('linkuri').strip())
			)

		procStr(string[done:])

	def as_funyu(self):
		return ''.join(
			elm.as_funyu() if isinstance(elm, Element) else elm
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
	>>> l.as_funyu()
	'this is test\\n'
	>>> l.as_html()
	'this is test<br>\\n'
	"""

	def as_funyu(self):
		return '{0}\n'.format(String.as_funyu(self))

	def as_html(self):
		return '{0}<br>\n'.format(String.as_html(self))


class Keyword(String):
	""" keyword element

	>>> k = Keyword('this is test')
	>>> k.as_funyu()
	'[[this is test]]'
	>>> k.as_html()
	'<strong>this is test</strong>'
	"""

	def as_funyu(self):
		return '[[{0}]]'.format(String.as_funyu(self))

	def as_html(self):
		return '<strong>{0}</strong>'.format(String.as_html(self))


class Emphasis(String):
	""" emphasis element

	>>> e = Emphasis('this is test')
	>>> e.as_funyu()
	'<<this is test>>'
	>>> e.as_html()
	'<em>this is test</em>'
	"""

	def as_funyu(self):
		return '<<{0}>>'.format(String.as_funyu(self))

	def as_html(self):
		return '<em>{0}</em>'.format(String.as_html(self))


class Code(String):
	""" inline code element

	>>> c = Code('this is test')
	>>> c.as_funyu()
	'{{this is test}}'
	>>> c.as_html()
	'<code>this is test</code>'
	"""

	def __init__(self, text):
		String.__init__(self, '')
		self.text = text

	def as_funyu(self):
		return '{{{{{0}}}}}'.format(self.text)

	def as_html(self):
		return '<code>{0}</code>'.format(self.text)


class Link(String):
	""" link element

	>>> l = Link('test', './test.html')
	>>> l.as_funyu()
	'[test](./test.html)'
	>>> l.as_html()
	'<a href="./test.html">test</a>'

	>>> l = Link('blog', 'http://blanktar.jp/blog/')
	>>> l.as_funyu()
	'[blog](http://blanktar.jp/blog/)'
	>>> l.as_html()
	'<a href="http://blanktar.jp/blog/" target="_blank">blog</a>'
	"""

	def __init__(self, text, uri):
		String.__init__(self, text)
		self.uri = uri

	def as_funyu(self):
		return '[{0}]({1})'.format(String.as_funyu(self), self.uri)

	def as_html(self):
		if urlparse.urlparse(self.uri).scheme:
			return '<a href="{0}" target="_blank">{1}</a>'.format(
				self.uri,
				String.as_html(self)
			)
		else:
			return '<a href="{0}">{1}</a>'.format(self.uri, String.as_html(self))


class ImageLink(Link):
	""" image link element

	>>> l = ImageLink('test', 'test.png')
	>>> l.as_funyu() == '[IMG: test](test.png)'
	True
	>>> l.as_html() == '<a href="test.png"><img src="test.png" alt="test"></a>'
	True

	>>> l = ImageLink('test', 'http://blanktar.jp/test.png')
	>>> l.as_funyu() == '[IMG: test](http://blanktar.jp/test.png)'
	True
	>>> l.as_html() == (
	... 	'<a href="http://blanktar.jp/test.png" target="_blank">'
	... 	'<img src="http://blanktar.jp/test.png" alt="test">'
	... 	'</a>'
	... )
	True
	"""

	def __init__(self, alt, uri):
		Link.__init__(self, '', uri)
		self.alt = alt

	def as_funyu(self):
		return '[IMG: {0}]({1})'.format(self.alt, self.uri)

	def as_html(self):
		if urlparse.urlparse(self.uri).scheme:
			fmt = '<a href="{0}" target="_blank"><img src="{0}" alt="{1}"></a>'
		else:
			fmt = '<a href="{0}"><img src="{0}" alt="{1}"></a>'

		return fmt.format(self.uri, self.alt)


if __name__ == '__main__':
	import argparse
	import sys
	import json

	parser = argparse.ArgumentParser(description='funyu parser.')
	parser.add_argument(
		'-t', '--test',
		action='store_true', default=False,
		help='test source code.'
	)

	parser.add_argument(
		'file',
		nargs='?',
		type=argparse.FileType('r'), default=sys.stdin,
		help='source file. default is stdin.'
	)
	parser.add_argument(
		'-b', '--body',
		dest='mode', action='store_const', const='body', default='body',
		help="get HTML's body. It is default."
	)
	parser.add_argument(
		'-m', '--meta',
		dest='mode', action='store_const', const='meta',
		help='get metadata paragraph.'
	)
	parser.add_argument(
		'-j', '--json',
		dest='mode', action='store_const', const='json',
		help='get metadata as json.'
	)

	args = parser.parse_args()

	if args.test:
		import doctest
		if doctest.testmod(verbose=True).failed == 0:
			sys.exit(0)
		else:
			sys.exit(1)
	else:
		f = Funyu()

		f.parse(args.file.read())

		if args.mode == 'body':
			print(f.as_html())
		elif args.mode == 'meta':
			print(f.metadata.as_funyu().strip())
		elif args.mode == 'json':
			print(json.dumps(f.metadata))
