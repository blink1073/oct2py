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

% Remove the existing file before doing anything.
[err, msg] = unlink(output_file)

load(input_file, 'req')

response.success = true;
response.content = '';
response.result = '';
response.error = '';
response.ans = '';

close all hidden;

try

    % Add function path to current path
    if req.dname
        addpath(req.dname);
    end

    clear ans;

    if iscell(req.func_args)
        [resp{1:req.nargout}] = feval(req.func_name, req.func_args{:});
    else
        [resp{1:req.nargout}] = feval(req.func_name, req.func_args);
    end

    if exist('ans') == 1
      response.ans = ans;
    end;

    if req.nargout == 1
        response.result = resp{1};
    else
        response.result = resp;
    end

catch ME
    response.success = false;
    response.error = ME;
end

% save the response to the output file
save('-v6', '-mat-binary', output_file, 'response')

end %function
