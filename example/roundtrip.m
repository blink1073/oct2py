
function [x, class] = roundtrip(y)

  % returns the variable it was given, and optionally the class

  x = y;

  if nargout == 2

	 class = class(x);

  end

end
