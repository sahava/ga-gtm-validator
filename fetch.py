import argparse
import csv

from apiclient.discovery import build
from apiclient.http import BatchHttpRequest
import httplib2
from oauth2client import client
from oauth2client import file
from oauth2client import tools

from fetch_source import properties

ga_rows = {}
ga_sequence = []

gtm_rows = {}

gtm_model = {} 
    
    
def get_service(api_name, api_version, scope, client_secrets_path):
    """Get a service that communicates to a Google API.

    Args:
        api_name: string The name of the api to connect to.
        api_version: string The api version to connect to.
        scope: A list of strings representing the auth scopes to authorize for the
          connection.
        client_secrets_path: string A path to a valid client secrets file.

    Returns:
        A service that is connected to the specified API.
    """
    # Parse command-line arguments.
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[tools.argparser])
    flags = parser.parse_args([])

    # Set up a Flow object to be used if we need to authenticate.
    flow = client.flow_from_clientsecrets(
        client_secrets_path, scope=scope,
        message=tools.message_if_missing(client_secrets_path))

    # Prepare credentials, and authorize HTTP object with them.
    # If the credentials don't exist or are invalid run through the native client
    # flow. The Storage object will ensure that if successful the good
    # credentials will get written back to a file.
    storage = file.Storage(api_name + '.dat')
    credentials = storage.get()
    if credentials is None or credentials.invalid:
        credentials = tools.run_flow(flow, storage, flags)
    http = credentials.authorize(http=httplib2.Http())

    # Build the service object.
    service = build(api_name, api_version, http=http)

    return service


def get_custom_dims(service, aid, pid):
    # Get a list of all Google Analytics accounts for the authorized user, and write it into a csv.
    return service.management().customDimensions().list(
        accountId=aid,
        webPropertyId=pid,
    ).execute()


def get_analytics_data(service, dimension_id, profile_id):
    return service.data().ga().get(
      ids=profile_id,
      start_date='7daysAgo',
      end_date='today',
      metrics='ga:hits',
      dimensions=dimension_id).execute()


def get_container(service, aid, cid):
    # Get the live container
    return service.accounts().containers().versions().live(
        parent='accounts/%s/containers/%s' % (aid, cid)
    ).execute()


def main():
    # Define the auth scopes to request.
    gaScope = ['https://www.googleapis.com/auth/analytics.readonly']
    gtmScope = ['https://www.googleapis.com/auth/tagmanager.readonly']

    # Authenticate and construct service.
    gaService = get_service('analytics', 'v3', gaScope, 'client_secrets_ga.json')
    gtmService = get_service('tagmanager', 'v2', gtmScope, 'client_secrets_gtm.json')
    
    print "Starting Google Analytics custom dimension CSV compilation..."
    
    with open('dimensions.csv', 'wb') as csvfile:
        dimwriter = csv.writer(csvfile)
        first_row = ['']
        second_row = ['']
        
        for prop in properties:
            first_row.append(prop)
            first_row.append(prop)
            first_row.append(prop)
            first_row.append(prop)
            second_row.append('NAME')
            second_row.append('SCOPE')
            second_row.append('ACTIVE')
            second_row.append('HITS_LAST_7')
            gtm_model[prop] = []
            ga_sequence.append(prop)  
            
            print "Fetching dimensions for " + prop + "..."
            custom_dims = get_custom_dims(gaService, properties[prop]['gaAccountId'], properties[prop]['gaPropertyId'])
            for dimension in custom_dims.get('items', []):
                dim_id = dimension.get('id')
                print dim_id + " processing"
                if dim_id not in ga_rows:
                    ga_rows[dim_id] = {}
                if prop not in ga_rows[dim_id]:
                    ga_rows[dim_id][prop] = []
                ga_rows[dim_id][prop].append(dimension.get('name'))
                ga_rows[dim_id][prop].append(dimension.get('scope'))
                ga_rows[dim_id][prop].append(dimension.get('active'))
                if dimension.get('active') is True:
                    ga_rows[dim_id][prop].append(
                        get_analytics_data(gaService, dim_id, properties[prop]['gaProfileId'])['totalsForAllResults']['ga:hits']
                    )
                else:
                    ga_rows[dim_id][prop].append('-')

        first_row.sort()
        ga_sequence.sort() 
        
        dimwriter.writerow(first_row)
        dimwriter.writerow(second_row)
    
        for i in range(200):
            row = []
            dim_id = "ga:dimension" + str (i + 1)
            row.append(dim_id)
            for j in range(len(ga_sequence)):
                if dim_id in ga_rows and ga_sequence[j] in ga_rows[dim_id] and len(ga_rows[dim_id][ga_sequence[j]]) > 0:
                    row.append(ga_rows[dim_id][ga_sequence[j]][0])
                    row.append(ga_rows[dim_id][ga_sequence[j]][1])
                    row.append(ga_rows[dim_id][ga_sequence[j]][2])
                    row.append(ga_rows[dim_id][ga_sequence[j]][3])
                else:
                    row.append('')
                    row.append('')
                    row.append('')
                    row.append('')
            dimwriter.writerow(row)    
      
    print "Starting Google Tag Manager UA tag CSV compilation..."
    
    for prop in properties:
        print "Fetching live container for " + prop + "..."
        latest = get_container(gtmService, properties[prop]['gtmAccountId'], properties[prop]['gtmContainerId'])
        for tag in latest.get('tag', []):
            if tag['type'] == 'ua':
                dimensions = {}
                trackingId = ''
                for param in tag['parameter']:
                    if param['key'] == 'trackingId':
                        trackingId = param['value']
                    if 'list' in param:
                        for item in param['list']:
                            if item['map'][0]['key'] == 'index':
                                dimensions["ga:dimension" + item['map'][0]['value']] = item['map'][1]['value']
                gtm_model[prop].append({
                    'name': tag['name'],
                    'dimensions': dimensions,
                    'trackingId': trackingId
                })
        with open('gtm_' + prop + '.csv', 'wb') as csvfile:
            print "Writing " + "gtm_" + prop + ".csv..."
            gtmrows = {}
            for i in range(200):
                gtmrows["ga:dimension" + str(i + 1)] = []
            gtmwriter = csv.writer(csvfile)
            first_row = ['']
            second_row = ['']
            for tag in gtm_model[prop]:
                first_row.append(tag['name'].encode('utf-8'))
                second_row.append(tag['trackingId'])
                for dim in gtmrows:
                    if dim in tag['dimensions']:
                        gtmrows[dim].append(tag['dimensions'][dim])
                    else:
                        gtmrows[dim].append('')
            gtmwriter.writerow(first_row)
            gtmwriter.writerow(second_row)
            for i in range(200):
                gtmrow = []
                gtmrow.append("ga:dimension" + str(i + 1))
                for item in gtmrows["ga:dimension" + str(i + 1)]:
                    gtmrow.append(item.encode('utf-8'))
                gtmwriter.writerow(gtmrow)    
    
    print "Done!"

if __name__ == '__main__':
    main()
    