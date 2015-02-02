.PHONY: cachebox-manager

all:cachebox-manager

cachebox-manager: Dockerfile
	docker build -t cachebox-manager . ;\
	chmod +x stomp.py

clean:
	rm -f *.pyc *.o *~
