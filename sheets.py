__author__ = 'rwest'

import pandas as pd
import numpy as np
import json
import keyring
import gspread
from oauth2client.service_account import ServiceAccountCredentials


def get_gdrive_client(credentials_key):
    """ Get gspread client

    Parameters
    ----------
    credentials_key : str
        either a path to a json file containing 'project_id' and 'read_key'
        or a service_name for keyring entries containing 'project_id' and
        'read_key'

    Returns
    -------
    gspread client
    """
    if credentials_key.endswith('.json'):
        credentionals_json = open(credentials_key, 'r').read()
    else:
        credentionals_json = keyring.get_password(credentials_key,
                                                 'credentionals_json')

    scope = ['https://spreadsheets.google.com/feeds']

    credentials = json.loads(credentionals_json)
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials,
                                                                   scope)
    gc = gspread.authorize(credentials)
    return gc


def write_to_sheets(gc, data, title, sheetname):
    """
    Add a timestamp in the first row then:

    Write the data in "data" to a google sheet named "title" on a new sheet
    "sheetname". If "sheetname" exists an error will be thrown.

    Parameters
    ----------
    gc : gspread.authorize
        google drive client
    data : pd.DataFrame
    title : str
        sheets title
    sheetname : str
        the sheetname in the google sheet
    """
    print 'writing to sheet: {}'.format(sheetname)

    wb = gc.open(title)
    wb.add_worksheet(title=sheetname, rows=1, cols=1)
    wks = wb.worksheet(sheetname)

    # add data
    for i, row in data.iterrows():
        wks.insert_row(values=row.tolist(), index=1)

    # add header row
    wks.insert_row(data.columns.tolist(), index=1)


def clean_sheets(gc, title, max_sheets):
    """
    Keep the number of sheets in the workbook to a maximum of 'max_sheets'.
    This method assumes the sheetname contains a time stamp in the first
    24 chars and will remove worksheets by ages until there are at most '
    max_sheets' If the sheet does not contain such a time stamp then it will
    not be removed

    Parameters
    ----------
    gc : gspread.authorize
        google drive client
    title : str
        sheets title
    max_sheets : str
        the maximum number of sheets to keep in the workbook
    """
    wb = gc.open(title)
    worksheets = wb.worksheets()

    if len(worksheets) <= max_sheets:
        return

    names = [w.title for w in worksheets]
    dates = []
    for name in names:
        try:
            date = pd.to_datetime(name[:24])
            dates.append(date)
        except ValueError:
            dates.append(np.nan)

    sheet_df = pd.DataFrame({'date': dates}, index=names).sort_values('date')
    num_drops = len(sheet_df) - max_sheets
    drop_sheet_df = sheet_df[:num_drops]

    print 'Sheet limit reached. {} sheets will be deleted'.format(
        len(drop_sheet_df))

    for ws in worksheets:
        if ws.title in drop_sheet_df.index:
            print 'deleting sheet: ' + ws.title
            wb.del_worksheet(ws)