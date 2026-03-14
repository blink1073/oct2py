% SimpleObj: minimal classdef fixture used by test_misc.py (issue #215).
classdef SimpleObj
  properties
    value = 0
    label = ''
  end
  methods
    function obj = SimpleObj(v, l)
      if nargin >= 1
        obj.value = v;
      end
      if nargin >= 2
        obj.label = l;
      end
    end
  end
end
