
(function () { /* hackadihack: make dotmenus close onclick anywhere. */
  document.getElementsByTagName('body')[0].addEventListener('click',
    function (ev) {
      var els = document.querySelectorAll('nav.dotmenu input[type="checkbox"]');
      for (var i = 0; i < els.length; i++) {
        if (els[i] != ev.target && els[i].checked) {
          els[i].checked = false;
        }
      }
    }
  );
})();

function getRandom(min, max) {
  // Return a random Float between min and max.
  return Math.random() * (max - min) + min;
}

function geoloc(form) {
  // Find user's geolocation, fuzzy it, and submit to profile.
  // See http://diveintohtml5.info/geolocation.html
  if (!"geolocation" in navigator) {
    alert("Your browser doesn't support geo location lookup.")
    return false;
  }

  function fuzzyGeoloc(lat, lng, fuzzyKm) {
        // Check if valid
        if (!lat || !lng) throw "No valid geolocation coords found.";
        // Fuzzy it by +/- x km, but we need that in degrees lat/lng.
        var latOneDegInKm = 110.574; // km
        var lngOneDegInKm = 111.320 * Math.cos(lat); // km
        // Get the degrees for 5 km.
        var latFuzzyDeg = fuzzyKm / latOneDegInKm;
        var lngFuzzyDeg = fuzzyKm / lngOneDegInKm;
        // Get a random number, (+ or -) for the degrees and add
        // it to the geolocation.
        var latRandomDeg = getRandom((latFuzzyDeg*(-1)), latFuzzyDeg);
        var lngRandomDeg = getRandom((lngFuzzyDeg*(-1)), lngFuzzyDeg);
        // Return the exacy lat/lng +/- the random degrees.
        return {'lat':(lat + latRandomDeg), 'lng':(lng + lngRandomDeg)};
  }

  try {
    // The callback gets a geolocation object and the time. Use only
    // "loc.coords.latitude" and "loc.coords.longitude", but fuzzy it!
    navigator.geolocation.getCurrentPosition(
      function(loc, timestamp) {
        // Fuzzy the geolocation with some +/- 5 kilometers. See
        // http://stackoverflow.com/questions/1253499/simple-calculations-
        //                            for-working-with-lat-lon-km-distance
        //
        // Approximation:
        // - Latitude: 1 deg = 110.574 km
        // - Longitude: 1 deg = 111.320 * cos(latitude) km
        //
        // Get geoloction from browser object.
        fuzzyCoords = fuzzyGeoloc(loc.coords.latitude, loc.coords.longitude,
                                  form.children.fuzzy.value);
        // Now set the fuzzy values on the form and submit.
        form.children.lat.value = fuzzyCoords.lat;
        form.children.lng.value = fuzzyCoords.lng;
        // Now submit the form.
        form.method = "POST"
        form.submit();
      }
    );
  } catch(err) {
    alert("Sorry, could not find your geolocation: " + err);
  }
}
