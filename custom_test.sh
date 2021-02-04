#!/bin/bash
test="pytest --no-cov $1"
$test $params aries_cloudagent/verifier/tests/test_pds.py 
# $test $params aries_cloudagent/issuer/tests/test_pds.py 
$test aries_cloudagent/holder/tests/test_holder_pds.py
# $test $params aries_cloudagent/protocols/issue_credential/v1_1/tests 
# $test $params aries_cloudagent/pdstorage_thcf/tests 
       
