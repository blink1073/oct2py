try
  a = ones2;
catch ME
  warning(ME.identifier, ME.message);
  exit(0)
end_try_catch
exit(1)
