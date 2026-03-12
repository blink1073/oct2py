% Octave script that accesses arguments via the argv workspace variable.
% When called via oct2py feval with arguments, argv is set as a cell array
% in the base workspace (issue #332).
disp(argv{1});
