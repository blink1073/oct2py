function result = test_recurse(n)
%TEST_RECURSE Return the sum 1+2+...+n via recursion.
  if n <= 0
    result = 0;
  else
    result = n + test_recurse(n - 1);
  end
end
