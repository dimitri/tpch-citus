# Makefile adapted from Makefile.suite

CC      = gcc
DATABASE = POSTGRESQL
MACHINE  = LINUX
WORKLOAD = TPCH

PG_CONFIG ?= pg_config
PG_INCLUDE = $(shell $(PG_CONFIG) --includedir)
PG_LIB     = $(shell $(PG_CONFIG) --libdir)

CFLAGS	= -g -DDBNAME=\"dss\" -D$(MACHINE) -D$(DATABASE) -D$(WORKLOAD) -DRNG_TEST -D_FILE_OFFSET_BITS=64 -I$(PG_INCLUDE) -I../lib
LDFLAGS = -O -L$(PG_LIB) -lpq

# The OBJ,EXE and LIB macros will need to be changed for compilation under
#  Windows NT
OBJ     = .o
EXE     =
LIBS    = -lm

#
# NO CHANGES SHOULD BE NECESSARY BELOW THIS LINE
###############

VERSION=2
RELEASE=13
PATCH=0
BUILD=`grep BUILD ../release.h | cut -f3 -d' '`
NEW_BUILD=`expr ${BUILD} + 1`
TREE_ROOT=/tmp/tree
#
PROG1 = dbgen$(EXE)
PROG2 = qgen$(EXE)
PROGS = $(PROG1) $(PROG2)
#
HDR1 = dss.h rnd.h config.h dsstypes.h shared.h bcd2.h rng64.h release.h \
       ../lib/pqexpbuffer.h
HDR2 = tpcd.h permute.h
HDR  = $(HDR1) $(HDR2)
#
SRC1 = build.c driver.c bm_utils.c rnd.c print.c load_stub.c bcd2.c \
	speed_seed.c text.c permute.c rng64.c ../lib/pqexpbuffer.c
SRC2 = qgen.c varsub.c 
SRC  = $(SRC1) $(SRC2)
#
OBJ1 = build$(OBJ) driver$(OBJ) bm_utils$(OBJ) rnd$(OBJ) print$(OBJ) \
	load_stub$(OBJ) bcd2$(OBJ) speed_seed$(OBJ) text$(OBJ) permute$(OBJ) \
	rng64$(OBJ)
OBJ2 = build$(OBJ) bm_utils$(OBJ) qgen$(OBJ) rnd$(OBJ) varsub$(OBJ) \
	text$(OBJ) bcd2$(OBJ) permute$(OBJ) speed_seed$(OBJ) rng64$(OBJ)
OBJS = $(OBJ1) $(OBJ2)
#
SETS = dists.dss 
DOC=README HISTORY PORTING.NOTES BUGS
DDL  = dss.ddl dss.ri
#
DBGENSRC=$(SRC1) $(HDR1) $(SRC2) $(HDR2)

ALLSRC=$(DBGENSRC)
JUNK  = 
#
all: $(PROGS)
$(PROG1): $(OBJ1) $(SETS) 
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $(OBJ1) $(LIBS)
$(PROG2): permute.h $(OBJ2) 
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $(OBJ2) $(LIBS)
clean:
	rm -f $(PROGS) $(OBJS) $(JUNK)
lint:
	lint $(CFLAGS) -u -x -wO -Ma -p $(SRC1)
	lint $(CFLAGS) -u -x -wO -Ma -p $(SRC2)

tar: $(ALLSRC) 
	find . -type d -name .svn -print > XLIST
	tar cvhfX - XLIST $(ALLSRC) |gzip - > tpch_${VERSION}_${RELEASE}_${PATCH}.tar.gz
	tar cvhfX - XLIST $(REFERENCE_DATA) |gzip - > reference_${VERSION}_${RELEASE}_${PATCH}.tar.gz
zip: $(ALLSRC)
	zip -r tpch_${VERSION}_${RELEASE}_${PATCH}.zip $(ALLSRC) -x *.svn*
	zip -r reference_${VERSION}_${RELEASE}_${PATCH}.zip $(REFERENCE_DATA) -x *.svn*
release: update_release
	make -f makefile.suite tar
	make -f makefile.suite zip
	( cd tests; sh test_list.sh `date '+%Y%m%d'` )
rnd$(OBJ): rnd.h
$(OBJ1): $(HDR1)
$(OBJ2): dss.h tpcd.h config.h rng64.h release.h
update_release:
	chmod 755 update_release.sh
	./update_release.sh ${VERSION} ${RELEASE} ${PATCH}
