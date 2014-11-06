SUBDIRS = storage

.PHONY: subdirs $(SUBDIRS)
subdirs: $(SUBDIRS)
$(SUBDIRS):
	$(MAKE) -C $@

.PHONY: clean
clean:
	rm -f *.pyc *.o *.log
	-for d in $(SUBDIRS); do (cd $$d; $(MAKE) clean ); done
