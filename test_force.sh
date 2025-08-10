#!/bin/bash

echo "Testing QMK Field Kit with --force flag"
echo "======================================"

echo ""
echo "1. Testing normal flash (should work)"
./flash.sh left

echo ""
echo "2. Testing cross-side flash without --force (should be blocked)"
./flash.sh right

echo ""
echo "3. Testing cross-side flash with --force (should work with warning)"
./flash.sh right --force

echo ""
echo "4. Testing reverse direction"
./flash.sh left --force

echo ""
echo "All tests completed."