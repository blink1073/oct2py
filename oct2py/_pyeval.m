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
%         workspace, instead of returning a value.
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
    for idx=1:length(req.ref_indices)
      ref_index = req.ref_indices(idx);
      var_name = req.func_args{ref_index};
      req.func_args{ref_index} = evalin('base', var_name);
    end

    assignin('base', 'ans', sentinel);

    % Use the `ans` response if no output arguments are expected.
    if req.nout == 0

        if length(req.func_args)
          try
            feval(req.func_name, req.func_args{:});
          catch ME
            if ~isempty(strfind(ME.message, 'invalid call to script'))
              assignin('base', 'argv', req.func_args);
              try
                evalin('base', req.func_name);
              catch ME2
                evalin('base', 'clear argv');
                rethrow(ME2);
              end
              evalin('base', 'clear argv');
            else
              rethrow(ME);
            end
          end
        else
          feval(req.func_name)
        end

        result = get_ans(sentinel);

    elseif length(req.func_args)
      try
        [result{1:req.nout}] = feval(req.func_name, req.func_args{:});
      catch ME
        if ~isempty(strfind(ME.message, 'invalid call to script'))
          assignin('base', 'argv', req.func_args);
          try
            evalin('base', req.func_name);
          catch ME2
            evalin('base', 'clear argv');
            rethrow(ME2);
          end
          evalin('base', 'clear argv');
          result = get_ans(sentinel);
        elseif (strcmp(ME.message, 'element number 1 undefined in return list') != 1 ||
            length(ME.stack) != 1)
          rethrow(ME);
        else
          result = get_ans(sentinel);
        end

      end

    else
      try
        [result{1:req.nout}] = feval(req.func_name);
      catch ME
        if ~isempty(strfind(ME.message, 'invalid call to script'))
          evalin('base', req.func_name);
          result = get_ans(sentinel);
        elseif (strcmp(ME.message, 'element number 1 undefined in return list') != 1 ||
            length(ME.stack) != 1)
          rethrow(ME);
        end
      end
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
  save_safe_struct(output_file, result, err);
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

function save_safe_struct(output_file, result, err)
    % NOTE: result is cell{1,1} containing other data
    try
        warn_state = warning('off', 'all');
        save('-v6', '-mat-binary', output_file, 'result', 'err');
        warning(warn_state);
    catch ME
        warning(warn_state);
        % Recursively coerce result to types that MAT v6 can serialize.
        result{1,1} = coerce_value(result{1,1});
        save('-v6', '-mat-binary', output_file, 'result', 'err');
    end
end

function val = coerce_value(val)
    % Recursively make val serializable to MAT v6 format.
    %   - structs/cells: recurse into fields/elements
    %   - function handles: convert to string via func2str
    %   - classdef/user objects: convert to struct via struct(), then recurse
    %   - unknown types: replace with [] and emit a warning
    primitive_types = {'double', 'single', 'char', 'logical', 'sparse', ...
                       'int8', 'int16', 'int32', 'int64', ...
                       'uint8', 'uint16', 'uint32', 'uint64'};
    if isstruct(val)
        fields = fieldnames(val);
        for i = 1:numel(fields)
            f = fields{i};
            val.(f) = coerce_value(val.(f));
        end
    elseif iscell(val)
        for i = 1:numel(val)
            val{i} = coerce_value(val{i});
        end
    elseif any(strcmp(class(val), primitive_types))
        % already serializable — return as-is
    elseif isa(val, 'function_handle')
        val = func2str(val);
    else
        % Unknown/user-defined type: try object-to-struct conversion first.
        try
            val = coerce_value(struct(val));
            return;
        catch
        end
        warning('oct2py:pyeval:save_safe_struct:UnacceptableType', ...
                'Replacing value of class "%s" with [] as it is not serializable.', ...
                class(val));
        val = [];
    end
end
