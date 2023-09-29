from django.shortcuts import render
from datetime import datetime, timedelta
from pytz import timezone
from zmanim.zmanim_calendar import ZmanimCalendar
from zmanim.util.geo_location import GeoLocation
import plotly.graph_objects as go
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderInsufficientPrivileges
from timezonefinder import TimezoneFinder

geolocator = Nominatim(user_agent="YourUniqueUserAgent")
tf = TimezoneFinder()

def get_location_coordinates(location):
    try:
        location = geolocator.geocode(location)
        if location:
            return location.latitude, location.longitude, location.raw['display_name']
        return None, None, None
    except (GeocoderTimedOut, GeocoderInsufficientPrivileges):
        return None, None, None

def get_timezone_from_lat_lng(lat, lng):
    return tf.timezone_at(lat=lat, lng=lng)

def time_to_float(t):
    return t.hour + t.minute / 60 + t.second / 3600

def float_to_time_string(x):
    hours = int(x)
    minutes = int((x * 60) % 60)
    seconds = int((x * 3600) % 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def generate_chart(zmanim_data, zmanim_options):
    fig = go.Figure()

    for location_name, zmanim in zmanim_data.items():
        labels = []
        data_dict = {opt: [] for opt in zmanim_options}
        hover_texts = {opt: [] for opt in zmanim_options}

        for date, times in zmanim.items():
            labels.append(date)
            for opt in zmanim_options:
                y_value = time_to_float(times[opt].time()) if times[opt] else None
                hover_text = float_to_time_string(y_value) if y_value else 'N/A'
                data_dict[opt].append(y_value)
                hover_texts[opt].append(hover_text)

        for opt in zmanim_options:
            fig.add_trace(go.Scatter(x=labels, y=data_dict[opt], mode='lines+markers', name=f"{opt} in {location_name}",
                                     hovertext=hover_texts[opt], hoverinfo="x+text"))

    tickvals = [i for i in range(0, 25)]
    ticktext = [float_to_time_string(i) for i in range(0, 25)]

    fig.update_layout(
        title='Zmanim Comparison',
        xaxis_title='Date',
        yaxis_title='Time',
        yaxis=dict(
            tickvals=tickvals,
            ticktext=ticktext
        )
    )

    chart_div = fig.to_html(full_html=False, default_height=500, default_width=700)
    return chart_div





def index(request):
    return render(request, 'index.html')

def compare_locations(request):
    if request.method == 'POST':
        locations_str = request.POST.get('locations')
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        zmanim_options = request.POST.getlist('zmanim_options')

        start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        locations = locations_str.split(',')
        zmanim_data = {}

        current_date = start_date_obj
        while current_date <= end_date_obj:
            for location in locations:
                latitude, longitude, display_name = get_location_coordinates(location.strip())
                if latitude and longitude:
                    time_zone_str = get_timezone_from_lat_lng(latitude, longitude)
                    geo_location = GeoLocation(latitude=latitude, longitude=longitude, name="Some Location", time_zone=time_zone_str)
                    zmanim_cal = ZmanimCalendar(geo_location=geo_location, date=current_date)
                    zmanim = {opt: getattr(zmanim_cal, opt)().astimezone(timezone(time_zone_str)) for opt in zmanim_options}

                    if display_name not in zmanim_data:
                        zmanim_data[display_name] = {}
                    
                    zmanim_data[display_name][current_date.strftime('%Y-%m-%d')] = zmanim

            current_date += timedelta(days=1)

        chart_div = generate_chart(zmanim_data, zmanim_options)
        return render(request, 'compare_locations.html', {'chart_div': chart_div})

    return render(request, 'compare_locations.html')


