SUBDIRS = nfs40

.PHONY: subdirs $(SUBDIRS)
subdirs: $(SUBDIRS)
$(SUBDIRS):
	$(MAKE) -C $@

.PHONY: clean
clean:
	rm -f *.pyc *.o
	-for d in $(SUBDIRS); do (cd $$d; $(MAKE) clean ); done
