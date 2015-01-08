SUBDIRS = base namenode datanode

.PHONY: subdirs $(SUBDIRS)
subdirs: $(SUBDIRS)
$(SUBDIRS):
	$(MAKE) -C $@

.PHONY: clean
clean:
	-for d in $(SUBDIRS); do (cd $$d; $(MAKE) clean ); done
