% SimpleObj: minimal classdef used by test_misc.py to exercise issue #215.
% A classdef object that Octave cannot save with -v6 -mat-binary.
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
