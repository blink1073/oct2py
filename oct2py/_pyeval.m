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
          feval(req.func_name, req.func_args{:});
        else
          feval(req.func_name)
        end

        result = get_ans(sentinel);

    elseif length(req.func_args)
      try
        [result{1:req.nout}] = feval(req.func_name, req.func_args{:});
      catch ME
        if (strcmp(ME.message, 'element number 1 undefined in return list') != 1 ||
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
          rethrow(ME);
        if (strcmp(ME.message, 'element number 1 undefined in return list') != 1 ||
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
    % warning('off', 'Octave:classdef-to-struct');
    try
        warn_state = warning('off', 'all');
        save('-v6', '-mat-binary', output_file, 'result', 'err');
        warning(warn_state);
    catch ME
        warning(warn_state);
        % handle failure in passing user defined object
        acceptable_types = {'double', 'char', 'logical', 'sparse'};
        if isstruct(result{1,1})
            result{1,1} = clean_struct(result{1,1}, acceptable_types);
        elseif iscell(result{1,1})
            result{1,1} = clean_cell(result{1,1}, acceptable_types);
        end
        save('-v6', '-mat-binary', output_file, 'result', 'err');
    end
end

function struct_out = clean_struct(struct_in, acceptable_types)
    fields = fieldnames(struct_in);
    struct_out = struct_in;
    for i = 1:numel(fields)
        field_value = struct_in.(fields{i});
        if ~is_acceptable_type(field_value, acceptable_types)
            warning(...
                'oct2py:pyeval:save_safe_struct:UnacceptableType', ...
                'Skipping field "%s" as it is not an acceptable type.', ...
                fields{i} ...
            );
            struct_out = rmfield(struct_out, fields{i});
        elseif isstruct(field_value)
            struct_out.(fields{i}) = clean_struct(field_value, acceptable_types);
        elseif iscell(field_value)
            struct_out.(fields{i}) = clean_cell(field_value, acceptable_types);
        end
    end
end

function cell_out = clean_cell(cell_in, acceptable_types)
    cell_out = cell_in;
    for i = 1:numel(cell_in)
        if ~is_acceptable_type(cell_in{i}, acceptable_types)
            warning(...
              'oct2py:pyeval:save_safe_struct:UnacceptableType', ...
              'Skipping cell content at index {%d} as it is not an acceptable type.', ...
              i ...
            );
            cell_out{i} = [];
        elseif isstruct(cell_in{i})
            cell_out{i} = clean_struct(cell_in{i}, acceptable_types);
        elseif iscell(cell_in{i})
            cell_out{i} = clean_cell(cell_in{i}, acceptable_types);
        end
    end
end

function result = is_acceptable_type(value, acceptable_types)
    if isstruct(value)
        result = all(structfun(@(v) is_acceptable_type(v, acceptable_types), value));
    elseif iscell(value)
        result = all(cellfun(@(v) is_acceptable_type(v, acceptable_types), value));
    else
        result = any(strcmp(class(value), acceptable_types));
    end
end
