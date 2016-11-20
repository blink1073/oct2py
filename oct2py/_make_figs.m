%% Create files for the currently open figures
function _make_figs(plot_dir, plot_name, plot_format, plot_offset, plot_res)

_figHandles = get(0, 'children');

for _fig=1:length(_figHandles),
    _handle = _figHandles(_fig);
    _filename = sprintf('%s/%s%03d.%s', plot_dir, plot_name, _fig + plot_offset, plot_format);
    try
       _image = double(get(get(get(_handle,'children'),'children'),'cdata'));
       _clim = get(get(_handle,'children'),'clim');
       _image = _image - _clim(1);
       _image = _image ./ (_clim(2) - _clim(1));
       imwrite(uint8(_image*255), _filename);
    catch
        print(_handle, _filename, sprintf('-r%s', plot_res));
    close(_handle);
end;

end;
