function _pyeval(input_file, output_file)
% _PYEVAL: Load a request from an input file, execute the request, and save
%         the response to the output file.
%
%   This allows you to run any Octave code. req should be a struct with the
%   following fields:
%       dname: The name of a directory to add to the runtime path before attempting to run the code.
%       func_name: The name of a function to invoke.
%       func_args: An array of arguments to send to the function.
%       nout: An int specifying how many output arguments are expected.
%       ref_indices: The indices of in the func_args that should
%         be replaced by the value represented by their name.
%       store_as: Optional name to store the return value in the base
%         workspace, instead of returing a value.
%
%   Should save a file containing the result object.
%
% Based on Max Jaderberg's web_feval

sentinel = { '__no_value__' };
result = { sentinel };
err = '';

try
    % Store the simple response in case we don't make it through the script.
    save('-v6', '-mat-binary', output_file, 'result', 'err');

    req = load(input_file);

    % Add function path to current path.
    if req.dname
        addpath(req.dname);
    end

    % Replace the names at the specified indices with their values.
    for index=1:length(req.ref_indices)
      ref_index = req.ref_indices(index);
      var_name = req.func_args{ref_index};
      req.func_args{ref_index} = evalin('base', var_name);
    end

    assignin('base', 'ans', sentinel);

    % Use the `ans` response if no output arguments are expected.
    if req.nout == 0
        
        if length(req.func_args)
          feval(req.func_name, req.func_args{:});
        else
          feval(req.func_name)
        end

        result = get_ans(sentinel);

    elseif length(req.func_args)
      try
        [result{1:req.nout}] = feval(req.func_name, req.func_args{:});
      catch ME
        if (strcmp(ME.message, 'element number 1 undefined in return list') != 1) 
          error(ME);
        else
          result = get_ans(sentinel);
        end
          
      end

    else
        [result{1:req.nout}] = feval(req.func_name);
    end

    if req.store_as
      assignin('base', req.store_as, result{1});
      result = { sentinel };
    end

    if ((strcmp(get(0, 'defaultfigurevisible'), 'on') == 1) &&
        length(get(0, 'children')))
      drawnow('expose');
    end

catch ME
    err = ME;
end


% Save the output to a file.
try
  save('-v6', '-mat-binary', output_file, 'result', 'err');
catch ME
  result = { sentinel };
  err = ME;
  save('-v6', '-mat-binary', output_file, 'result', 'err');
end 

end  % function


function result = get_ans(sentinel)
    try
      [result{1}] = evalin('base', 'ans');
    catch
      result = { sentinel };
    end
end
