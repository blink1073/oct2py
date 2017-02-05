try
  a = ones2;
catch err
  warning(err.identifier, err.message);
  exit(0)
end_try_catch
exit(1)
