function _pyeval(input_file, output_file)
% _PYEVAL: Load a request from an input file, execute the request, and save
%         the response to the output file.
%
%   This allows you to run any Octave code. req should be a struct with the
%   following fields:
%       dname: The name of a directory to add to the runtime path before attempting to run the code.
%       func_name: The name of a function to invoke.
%       func_args: An array of arguments to send to the function.
%       nargout: An int specifying how many output arguments are expected.
%
%   Should save a file containing the result object.
%
% Based on Max Jaderberg's web_feval

response.result = '';
response.error = '';

try
    close all hidden; 

    % Remove the existing file before doing anything.
    [err, msg] = unlink(output_file);

    load(input_file, 'req');

    % Add function path to current path
    if req.dname
        addpath(req.dname);
    end

    assignin('base', 'ans', '');

    % Replace the names at the specified indices with their values.
    for index=1:length(req.replacement_indices)
      repl_index = req.replacement_indices(index);
      var_name = req.func_args{repl_index};
      req.func_args{repl_index} = evalin('base', var_name);
    end

    if req.nout == 0
        feval(req.func_name, req.func_args{:});
        resp = evalin('base', 'ans');
    elseif iscell(req.func_args)
        [resp{1:req.nout}] = feval(req.func_name, req.func_args{:});
    else
        [resp{1:req.nout}] = feval(req.func_name, req.func_args);
    end

    if req.nout == 1
        response.result = resp{1};
    else
        response.result = resp;
    end

    if req.store_as
      assignin('base', req.store_as, response.result);
      response.result = '';
    end

catch ME;
    response.error = ME;
end


% Save the output to a file.
try
  save('-v6', '-mat-binary', output_file, 'response');
catch ME;
  response.result = '';
  response.error = ME;
  save('-v6', '-mat-binary', output_file, 'response');
end 

end  % function
