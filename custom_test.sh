#!/bin/bash
test="pytest --no-cov $1"
$test aries_cloudagent/verifier/tests/test_pds.py 
$test aries_cloudagent/issuer/tests/test_pds.py 
$test aries_cloudagent/holder/tests/test_holder_pds.py
# $test aries_cloudagent/protocols/issue_credential/v1_1/tests 
$test aries_cloudagent/pdstorage_thcf/tests 
       
