"""Settings for oct2py sessions."""
# Copyright (c) oct2py developers.
# Distributed under the terms of the MIT License.

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Oct2PySettings(BaseSettings):
    """Settings for an Oct2Py session.

    Can be populated from environment variables (prefixed with ``OCT2PY_``),
    a ``.env`` file, or programmatically.

    Attributes
    ----------
    model_config : SettingsConfigDict
        Pydantic-settings configuration: ``env_prefix="OCT2PY_"``,
        ``populate_by_name=True``.
    executable : str, optional
        Path to the Octave executable. Resolved in order: this argument,
        ``OCTAVE_EXECUTABLE`` env var, ``octave``/``octave-cli`` on
        ``PATH``, then Flatpak.
    timeout : float, optional
        Timeout in seconds for Octave commands.
    oned_as : str
        If ``"column"``, write 1-D numpy arrays as column vectors.
        If ``"row"`` (default), write 1-D numpy arrays as row vectors.
    temp_dir : str, optional
        Directory for MAT files.
    convert_to_float : bool
        If True (default), convert integer types to float when passing to Octave.
    backend : str
        The graphics_toolkit to use for plotting. Use ``"disable"`` to suppress
        all figure rendering.
    keep_matlab_shapes : bool
        If True, preserve MATLAB shapes (e.g. scalars as (1,1)).
    auto_show : bool, optional
        If True, automatically display figures after each call.
    plot_format : str
        Default format for saved plots (default ``"svg"``).
    plot_name : str
        Default base name for saved plots (default ``"plot"``).
    plot_width : int, optional
        Default plot width in pixels.
    plot_height : int, optional
        Default plot height in pixels.
    plot_res : int, optional
        Default plot resolution in pixels per inch.
    extra_cli_options : str
        Extra command-line options appended to the Octave invocation.
    load_octaverc : bool
        If True (default), source ``~/.octaverc`` during startup.  Set to
        False to skip loading the user init file, which is useful in
        reproducible or sandboxed environments where the init file may
        alter the path, set conflicting options, or is simply unavailable.

    Examples
    --------
    >>> s = Oct2PySettings(backend="disable", timeout=30)
    >>> s.backend
    'disable'
    >>> s.timeout
    30.0
    """

    model_config = SettingsConfigDict(
        env_prefix="OCT2PY_",
        populate_by_name=True,
    )

    # Octave executable — reads OCTAVE_EXECUTABLE or OCTAVE env vars
    executable: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OCTAVE_EXECUTABLE", "OCTAVE"),
    )

    # Session settings
    timeout: float | None = None
    oned_as: str = "row"
    temp_dir: str | None = None
    convert_to_float: bool = True
    backend: str = "default"
    keep_matlab_shapes: bool = False
    auto_show: bool | None = None

    # Plot defaults
    plot_format: str = "svg"
    plot_name: str = "plot"
    plot_width: int | None = None
    plot_height: int | None = None
    plot_res: int | None = None
    extra_cli_options: str = ""
    load_octaverc: bool = True
