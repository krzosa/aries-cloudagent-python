echo "--------------------------------------------------------------------"
echo "Make sure to start the script from aries-cloudagent-python directory"
echo "--------------------------------------------------------------------"

cd keri-python-ffi
cargo build
scripts/build_python.sh
cd ffi/python/libs/
cp libkel_utils.so ../../../../aries_cloudagent/wallet