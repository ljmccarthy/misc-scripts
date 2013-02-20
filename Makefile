TARGET    = myprogram
SRCDIRS   = src
INCDIRS   = include
OBJDIR    = /tmp/$(TARGET)-build
LIBDIRS   =
DYNLIBS   =
LIBS      =
DEFINES   =
PKGS      =
CFLAGS    = -std=c++98 -Wall -W -fvisibility=hidden -fvisibility-inlines-hidden
LINKFLAGS =

ifeq ($(strip $(DEBUG)),)
  CFLAGS  += -Os -fomit-frame-pointer
  DEFINES += NDEBUG
else
  CFLAGS  += -ggdb
endif

PKG_CFLAGS = $(foreach pkg,$(PKGS),$(shell pkg-config --cflags $(pkg)))
PKG_LIBS   = $(foreach pkg,$(PKGS),$(shell pkg-config --libs $(pkg)))
CFLAGS    += $(PKG_CFLAGS) $(DEFINES:%=-D%) $(INCDIRS:%=-I%)
LIBFLAGS   = $(PKG_LIBS) $(LIBDIRS:%=-L%) $(DYNLIBS:%=-l%)
SRCFILES   = $(foreach dir,$(SRCDIRS),$(wildcard $(dir)/*.c)) \
             $(foreach dir,$(SRCDIRS),$(wildcard $(dir)/*.cxx))
DEPFILES   = $(SRCFILES:%=$(OBJDIR)/%.d)
OBJFILES   = $(SRCFILES:%=$(OBJDIR)/%.o)

.PHONY : all clean

all : $(TARGET)

clean :
	@rm -rf $(TARGET) $(OBJDIR)

$(OBJDIR)/%.c.o : %.c
	@echo " GCC      $<"
	@gcc -c -pipe -fPIC $(CFLAGS) -o $@ $<

$(OBJDIR)/%.cxx.o : %.cxx
	@echo " G++      $<"
	@g++ -c -pipe -fPIC $(CFLAGS) -o $@ $<

$(OBJDIR)/%.c.d : %.c
	@mkdir -p $(dir $@)
	@gcc -MM -MP -MT "$(OBJDIR)/$<.o" $(CFLAGS) $< > $@ || (rm -f $@; exit 1)

$(OBJDIR)/%.cxx.d : %.cxx
	@mkdir -p $(dir $@)
	@g++ -MM -MP -MT "$(OBJDIR)/$<.o" $(CFLAGS) $< > $@ || (rm -f $@; exit 1)

ifneq ($(MAKECMDGOALS),clean)
-include $(DEPFILES)
endif

$(TARGET) : $(OBJFILES)
	@echo " EXE      $@"
	@g++ -pipe $(LINKFLAGS) $(LIBFLAGS) -o $@ $(OBJFILES) $(LIBS)
ifeq ($(strip $(DEBUG)),)
	@strip -s -R .comment $@
endif
