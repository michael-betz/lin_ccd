BUILD_FOLDER = build
TOP_V   = $(BUILD_FOLDER)/gateware/top.v
TOP_BIT = $(BUILD_FOLDER)/gateware/top.bit
COMMON_OPTS = --output-dir $(BUILD_FOLDER) --csr-csv $(BUILD_FOLDER)/csr.csv

all: clean $(TOP_V)

$(TOP_V):
	python target_cmodA7.py $(COMMON_OPTS) --no-compile-gateware

$(TOP_BIT):
	python target_cmodA7.py $(COMMON_OPTS)

config: $(TOP_BIT)
	python -c "from litex.boards.platforms import cmod_a7;\
	 cmod_a7.Platform().create_programmer().load_bitstream('$^')"

test:
	-pkill litex_server*
	litex_server uart /dev/ttyUSB1&
	ipython -i test.py

clean:
	rm -rf $(BUILD_FOLDER)

.PHONY: clean lib load test all
