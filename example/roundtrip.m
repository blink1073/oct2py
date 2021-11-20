
function [x, cls] = roundtrip(y)

  % returns the variable it was given, and optionally the class

  x = y;

  if nargout == 2

	 cls = class(x);

  end

end
