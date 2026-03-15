% NoDefaultCtorClass: classdef fixture with a required-argument constructor.
% Used by test_misc.py to verify issue #174 (returning classdef objects
% whose constructor requires arguments does not raise an error).
classdef NoDefaultCtorClass
  properties
    value
    label
  end
  methods
    function obj = NoDefaultCtorClass(v, l)
      if nargin ~= 2
        error('NoDefaultCtorClass requires exactly two arguments');
      end
      obj.value = v;
      obj.label = l;
    end
    function r = doubled(obj)
      r = obj.value * 2;
    end
  end
end
