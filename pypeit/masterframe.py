"""
Implements the master frame base class.

.. _numpy.ndarray: https://docs.scipy.org/doc/numpy/reference/generated/numpy.ndarray.html
"""
import os
import warnings

from abc import ABCMeta

import numpy as np

from astropy.io import fits

from pypeit import msgs

class MasterFrame(object):
    """
    Base class for all PypeIt calibration master frames.

    Main methods of the class are to implement the default paths for the
    master frames and their I/O methods.

    Args:
        master_type (str):
            Master frame type, used when constructing the output file
            name.  See :attr:`file_name`.
        master_dir (str or None):
            Name of the MasterFrame folder, e.g. MF_keck_deimos. If
            None, set to './'
        master_key (str or None):
            Root of the MasterFrame names, e.g. 'A_1_01'.  If None, set
            to 'master'
        format (:obj:`str`, optional):
            File format for the master frame.  Typically 'fits' or 'json'.
        reuse_masters (bool, optional):
            Reuse already created master files from disk.

    Attributes:
        master_type (:obj:`str`):
            See initialization arguments.
        master_dir (:obj:`str`):
            See initialization arguments.
        master_key (:obj:`str`):
            See initialization arguments.
        format (:obj:`str`):
            See initialization arguments.
        format (:obj:`str`):
            See initialization arguments.
        reuse_masters (:obj:`bool`):
            See initialization arguments.
    """
    __metaclass__ = ABCMeta

    def __init__(self, master_type, master_dir=None, master_key=None, format='fits',
                 reuse_masters=False):

        # Output names
        self.master_type = master_type
        self.master_dir = os.getcwd() if master_dir is None else master_dir
        self.master_key = 'master' if master_key is None else master_key
        self.format = format

        # Other parameters
        self.reuse_masters = reuse_masters

#    @property
#    def ms_name(self):
#        """ Default filenames for MasterFrames
#
#        Returns:
#            str:  Master filename
#        """
#        return master_name(self.frametype, self.master_key, self.master_dir)
#
#    @property
#    def mdir(self):
#        """
#
#        Returns:
#            str: Master frames folder
#
#        """
#        return self.master_dir

    @property
    def file_name(self):
        """
        Name of the MasterFrame file.
        """
        return 'Master{0}_{1}.{2}'.format(self.master_type, self.master_key, self.format)

    @property
    def file_path(self):
        """
        Full path to MasterFrame file.
        """
        return os.path.join(self.master_dir, self.file_name)

# prev_build loads from memory, never from a file.  Use reuse_masters in
# load()
#    def master(self, prev_build=False):
#        """
#        Load the master frame from disk, as settings allows. This
#        routine checks the the mode of master usage then calls the
#        load_master method. This method should not be overloaded by
#        children of this class. Instead one should overload the
#        load_master method below.
#
#        Args:
#            prev_build (bool, optional):
#                If True, try to load master from disk
#
#        Returns:
#            ndarray or None:  Master image
#
#        """
#        # Are we loading master files from disk?
#        if self.reuse_masters or prev_build:
#            self.msframe, head = self.load_master(self.ms_name)
#            return self.msframe, head
#        else:
#            return None, None

    def save(self, data, extnames, outfile=None, overwrite=True, raw_files=None, steps=None):
        """
        Base interface for saving master frame image data to a fits
        file.

        Data is always placed in extensions, with the PRIMARY extension
        only containing the header data.  More complicated master frame
        data models should overload this function.

        Args:
            data (:obj:`list`, `numpy.ndarray`_):
                One or more data arrays to save.
            extnames (:obj:`list`, :obj:`str`):
                The names for the data extensions.
            outfile (:obj:`str`, optional):
                Name for the output file.  Defaults to
                :attr:`file_path`.
            overwrite (:obj:`bool`, optional):
                Overwrite any existing file.
            raw_files (:obj:`list`, optional):
                List of processed raw files used to construct the master
                frame.
            steps (:obj:`list`, optional):
                The list of steps executed by the derived class to
                construct the master frame.
        """
        _outfile = self.file_path if outfile is None else outfile
        # Check if it exists
        if os.path.exists(_outfile) and not overwrite:
            msgs.warn('Master file exists: {0}'.format(_outfile) + msgs.newline()
                      + 'Set overwrite=True to overwrite it.')
            return

        # Log
        msgs.info('Saving master frame to {0}'.format(_outfile))

        # Format the output
        ext = extnames if isinstance(extnames, list) else [extnames]
        if len(ext) > 1 and not isinstance(data, list):
            msgs.error('Input data type should be list, one numpy.ndarray per extension.')
        _data = data if isinstance(data, list) else [data]

        # Build the header
        hdr = fits.Header()
        #   - Set the master frame type
        hdr['FRAMETYP'] = (self.master_type, 'PypeIt: Master calibration frame type')
        #   - List the completed steps
        hdr['STEPS'] = (','.join(steps), 'Completed reduction steps')
        #   - Provide the file names
        if raw_files is not None:
            nfiles = len(raw_files)
            ndig = int(np.log10(nfiles))+1
            for i in range(nfiles):
                hdr['F{0}'.format(i+1).zfill(ndig)] = (raw_files[i], 'PypeIt: Processed raw file')
        
        # Write the fits file
        fits.HDUList([fits.PrimaryHDU(header=hdr)]
                        + [ fits.ImageHDU(data=d, name=n) for d,n in zip(_data, ext)]
                     ).writeto(_outfile, overwrite=True)

        msgs.info('Master frame written to {0}'.format(_outfile))

    # TODO: have ext default to provide all extensions?
    def load(self, ext, ifile=None, return_header=False):
        """
        Generic master file reader.

        This generic reader assumes the file is in fits format.
        
        Args:
            ext (:obj:`str`, :obj:`int`, :obj:`list`):
                One or more file extensions with data to return.  The
                extension can be designated by its 0-indexed integer
                number or its name.
            ifile (:obj:`str`, optional):
                Name of the master frame file.  Defaults to
                :attr:`file_path`.
            return_header (:obj:`bool`, optional):
                Return the header

        Returns:
            tuple: Returns the image data from each provided extension.
            If return_header is true, the primary header is also
            returned.  If nothing is loaded, either because
            :attr:`reuse_masters` is `False` or the file does not exist,
            everything is returned as None (one per expected extension
            and one if the header is requested).
        """
        # Format the input and set the tuple for an empty return
        _ifile = self.file_path if ifile is None else ifile
        _ext = ext if isinstance(ext, list) else [ext]
        n_ext = len(_ext)
        empty_return = ((None,)*(n_ext+1) if return_header else (None,)*n_ext) \
                            if n_ext > 1 or return_header else None
        if not self.reuse_masters:
            # User does not want to load masters
            msgs.warn('PypeIt will not reuse masters!')
            return empty_return
        
        if not os.path.isfile(_ifile):
            # Master file doesn't exist
            msgs.warn('No Master {0} frame found: {1}'.format(self.master_type, self.file_path))
            return empty_return

        # Read and return
        msgs.info('Loading Master {0} frame: {1}'.format(self.master_type, _ifile))
        hdu = fits.open(_ifile)
        # Only one extension
        if n_ext == 1:
            data = hdu[_ext[0]].data.astype(np.float)
            return (data, hdu[0].header) if return_header else data
        # Multiple extensions
        data = tuple([ hdu[k].data.astype(np.float) for k in _ext ])
        return data + (hdu[0].header,) if return_header else data

    @staticmethod
    def parse_hdr_raw_files(hdr):
        """
        Parse the file names written to the header by :func:`save`.

        Args:
            hdr (fits.Header):
                Astropy Header object
        
        Returns:
            list: The list of files ordered as they were listed in the
            header.
        """
        raw_files = {}
        prefix = 'F'
        for k, v in hdr.items():
            if k[:len(prefix)] == prefix:
                try:
                    i = int(k[len(prefix):])-1
                except ValueError:
                    continue
                raw_files[i] = v
        # Convert from dictionary with integer keys to an appropriately
        # sorted list
        return [ raw_files[i] for i in range(max(raw_files.keys())+1) ]
    
# Moved to each master frame child.  badpix, pinhole, sensfunc have no
# masterframe child...
#def master_name(ftype, master_key, mdir):
#    """ Default filenames for MasterFrames
#
#    Args:
#        ftype (str):
#          Frame type
#        master_key (str):
#          Setup name, e.b. A_1_01
#        mdir (str):
#          Master directory
#
#    Returns:
#        str: masterframe filename
#    """
#    name_dict = dict(bias='{:s}/MasterBias_{:s}.fits'.format(mdir, master_key),
#                     badpix='{:s}/MasterBadPix_{:s}.fits'.format(mdir, master_key),
#                     trace='{:s}/MasterTrace_{:s}.fits'.format(mdir, master_key),
#                     pinhole='{:s}/MasterPinhole_{:s}.fits'.format(mdir, master_key),
#                     pixelflat='{:s}/MasterPixelFlat_{:s}.fits'.format(mdir, master_key),
#                     illumflat='{:s}/MasterIllumFlat_{:s}.fits'.format(mdir, master_key),
#                     arc='{:s}/MasterArc_{:s}.fits'.format(mdir, master_key),
#                     wave='{:s}/MasterWave_{:s}.fits'.format(mdir, master_key),
#                     wv_calib='{:s}/MasterWaveCalib_{:s}.json'.format(mdir, master_key),
#                     tilts='{:s}/MasterTilts_{:s}.fits'.format(mdir, master_key),
#                     # sensfunc='{:s}/MasterSensFunc_{:s}_{:s}.yaml'.format(mdir, master_key[0], master_key[-2:]),
#                     sensfunc='{:s}/MasterSensFunc_{:s}_{:s}.fits'.format(mdir, master_key[0], master_key[-2:]),
#                     )
#    return name_dict[ftype]

# Moved to calibrations.py
#def set_master_dir(redux_path, spectrograph, par):
#    """
#    Set the master directory auto-magically
#
#    Args:
#        redux_path: str or None
#        spectrograph: Spectrograph or None
#        par: ParSet or None
#
#    Returns:
#        master_dir : str
#          Path of the MasterFrame directory
#
#    """
#    # Parameters
#    if par is None:
#        tmppar = pypeitpar.CalibrationsPar()
#    else:
#        if 'caldir' not in par.keys():
#            tmppar = pypeitpar.CalibrationsPar()
#        else:
#            tmppar = par
#    # Redux path
#    if redux_path is None:
#        redux_path = os.getcwd()
#    master_dir = os.path.join(redux_path, tmppar['caldir'])
#    # Spectrograph
#    if spectrograph is not None:
#        master_dir += '_'+spectrograph.spectrograph
#    # Return
#    return master_dir

