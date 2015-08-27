funyu
=====

**funyu** is markup language for blog posting.
This project is developed converter that funyu into HTML5.

## What is funyu?
funyu is markup language for my blog writing.
This language is improvement of [linaria](http://blanktar.jp/works/other/linaria/) for doing more exact markup.
About detail of funyu syntax, please read [reference](REFERENCE.fny).

## What is required?
python2.7 or later, or python3.x.

## How to use?
### From console
Not yet implemented.

### From python
Import funyu.py and instantiation Funyu class.
And, parse your funyu document.
```
	>>> import funyu
	>>> f = funyu.Funyu()
	>>> f.parse('''title: test

	this is test of [[funyu]].
	''')
```

Can you get parsed document as HTML5 or funyu.
```
	>>> print(f.as_html())
	<p>
	this is test of <strong>funyu</strong><br>
	</p>

	>>> print(f.as_funyu())
	title: test

	this is test of [[funyu]].
```

Please see pydoc, if you wants more detail.

## Author / License
[MIT License](http://opensource.org/licenses/MIT)
(c)2015 MacRat <macrater@gmail.com>
