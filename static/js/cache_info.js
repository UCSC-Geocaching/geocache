mapboxgl.accessToken =
  'pk.eyJ1IjoiY3N0ZXJ6YSIsImEiOiJjbDF0dDRleG0yMWpkM2Ztb3B0YWZoaTR6In0.09vTcRrP3ty1lWFuouDsiw'; //store in environ var.
// ##################################

// This will be the object that will contain the Vue attributes
// and be used to initialize it.
let app = {};

// Given an empty app object, initializes it filling its attributes,
// creates a Vue instance, and then initializes the Vue instance.
let init = (app) => {
  // This is the Vue data.
  app.data = {
    cache: {},
    cache_max_boxes: 5,
    bookmarked: false,
    cache_logs: [],
    button_disabled: false,
    refresh_time: {},
    map_src: '',
  };

  app.getCacheInfo = function () {
    axios.get(getCacheURL).then(function (r) {
      app.vue.cache = r.data.cache;
      app.getLogs();
      app.checkTimer();
      app.loadMap();
    });
    axios.get(getBookmarkedURL).then(function (r) {
      app.vue.bookmarked = r.data.bookmarked;
    });
  };

  app.bookmark = function () {
    axios.put(setBookmarkedURL).then(function (r) {
      app.vue.bookmarked = r.data.bookmarked;
    });
  };

  app.loadMap = function () {
    app.vue.map_src = `https://api.mapbox.com/styles/v1/mapbox/outdoors-v11/static/${app.vue.cache.long},${app.vue.cache.lat},17/1280x1280?access_token=pk.eyJ1IjoiY3N0ZXJ6YSIsImEiOiJjbDF0dDRleG0yMWpkM2Ztb3B0YWZoaTR6In0.09vTcRrP3ty1lWFuouDsiw`;
  };

  app.logCache = function () {
    axios.put(logCacheURL).then(function (r) {
      if (r.data.log != null) {
        app.getLogs();
      }
      app.checkTimer();
    });
  };

  app.getLogs = function () {
    axios.get(getLogsURL).then(function (r) {
      // Reverse chronological order
      tmpLogs = r.data.logs.reverse();
      // Format the dates
      tmpLogs.forEach((log) => {
        tmp_date = new Date(log.discover_date.replace(' ', 'T'));
        log.discover_month = tmp_date.getMonth() + 1;
        log.discover_day = tmp_date.getDate();
        log.discover_year = tmp_date.getFullYear();
      });
      // Get only up to 5 logs
      tmpLogs.length = Math.min(tmpLogs.length, 5);
      app.vue.cache_logs = tmpLogs;
    });
  };

  app.checkTimer = function () {
    axios.get(checkTimerURL).then(function (r) {
      app.vue.button_disabled = r.data.disabled;
      raw_datetime = new Date(r.data.refresh_time.replace(' ', 'T'));
      app.vue.refresh_time.month = raw_datetime.getMonth() + 1;
      app.vue.refresh_time.date = raw_datetime.getDate();
      app.vue.refresh_time.year = raw_datetime.getFullYear();
      app.vue.refresh_time.time = r.data.refresh_time.split(' ')[1];
    });
  };

  // This contains all the methods.
  app.methods = {
    getCacheInfo: app.getCacheInfo,
    // getUser: app.getUser,
    bookmark: app.bookmark,
    loadMap: app.loadMap,
    logCache: app.logCache,
    getLogs: app.getLogs,
    checkTimer: app.checkTimer,
  };

  // This creates the Vue instance.
  app.vue = new Vue({
    el: '#vue-target',
    data: app.data,
    methods: app.methods,
  });

  // And this initializes it.
  app.init = () => {
    // Put here any initialization code.
    // Typically this is a server GET call to load the data.
    app.getCacheInfo();
  };

  // Call to the initializer.
  app.init();
};

// This takes the (empty) app object, and initializes it,
// putting all the code i
init(app);
