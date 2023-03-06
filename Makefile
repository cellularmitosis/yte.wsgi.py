serve: tmp/AngleSharp.dll tmp/YoutubeExplode.dll
	mkdir -p tmp
	cp -a yte.wsgi.py tmp/
	cd tmp && ./yte.wsgi.py
.PHONY: serve

express: tmp/AngleSharp.dll tmp/YoutubeExplode.dll
	mkdir -p tmp
	cp -a yte.wsgi.py tmp/
	echo Run: tail -f /tmp/mod_wsgi-localhost\:8000\:1000/error_log
	cd tmp && mod_wsgi-express start-server yte.wsgi.py
.PHONY: express

tmp/AngleSharp.dll:
	mkdir -p tmp
	cd tmp && nuget install AngleSharp
	cd tmp && ln -sf AngleSharp.1.0.1/lib/net7.0/*.dll .

tmp/YoutubeExplode.dll:
	mkdir -p tmp
	cd tmp && curl -fLO https://github.com/cellularmitosis/YoutubeExplodeSync/raw/master/YoutubeExplode.dll

ubuntu-deps:
	sudo apt-get install nuget
	sudo apt-get install python3-pip apache2-dev
	sudo pip3 install -U mod_wsgi
.PHONY: ubuntu-deps
