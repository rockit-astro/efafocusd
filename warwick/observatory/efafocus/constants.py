#
# This file is part of efafocusd
#
# efafocusd is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# efafocusd is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with efafocusd.  If not, see <http://www.gnu.org/licenses/>.

"""Constants and status codes used by focusd"""

from warwick.observatory.common import TFmt


class CommandStatus:
    """Numeric return codes"""
    # General error codes
    Succeeded = 0
    Failed = 1
    Blocked = 2
    InvalidControlIP = 3

    PositionOutsideLimits = 6
    NotConnected = 7
    NotDisconnected = 8

    _messages = {
        # General error codes
        1: 'error: command failed',
        2: 'error: another command is already running',
        3: 'error: command not accepted from this IP',
        6: 'error: requested position outside channel range',
        7: 'error: focuser is not connected',
        8: 'error: focuser is already connected',

        -100: 'error: terminated by user',
        -101: 'error: unable to communicate with focus daemon',
    }

    @classmethod
    def message(cls, error_code):
        """Returns a human readable string describing an error code"""
        if error_code in cls._messages:
            return cls._messages[error_code]
        return f'error: Unknown error code {error_code}'


class FocuserStatus:
    """Status of the focuser hardware"""
    Disabled, Idle, Moving = range(3)

    _labels = {
        0: 'OFFLINE',
        1: 'IDLE',
        2: 'MOVING',
    }

    _formats = {
        0: TFmt.Bold + TFmt.Red,
        1: TFmt.Bold,
        2: TFmt.Bold + TFmt.Yellow,
    }

    @classmethod
    def label(cls, status, formatting=False):
        """Returns a human readable string describing a status
           Set formatting=true to enable terminal formatting characters
        """
        if formatting:
            if status in cls._formats and status in cls._formats:
                return cls._formats[status] + cls._labels[status] + TFmt.Clear
            return TFmt.Red + TFmt.Bold + 'UNKNOWN' + TFmt.Clear

        if status in cls._labels:
            return cls._labels[status]
        return 'UNKNOWN'
