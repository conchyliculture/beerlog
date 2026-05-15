function update_graph(path, func) {
    var xhttp = new XMLHttpRequest(), method = "GET", url=path;
    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            info = JSON.parse(xhttp.responseText);
            func(info['data']);
        }
    };
    xhttp.open(method, url, true);
    xhttp.send();
}
function drawChart(le_data) {
    console.log(le_data);
    var labels = le_data['labels'];
    var datasets = le_data['datasets'];
    var drinkers = le_data['drinkers'];

    var peakIndex = le_data['peak_3hr_start_index'];
    var peakWindowLength = le_data['peak_3hr_window_length'] || 3;
    var peakLabel = le_data['peak_3hr_label'] || (labels[peakIndex] || 'unknown');
    var peakByCharacter = le_data['peak_by_character'] || [];

    document.getElementById('total').innerHTML =
        'Total drunk: ' + le_data['total'] + 'L<br>' +
        'Top cumulative speed: ' + le_data['peak_total']['amount'].toFixed(2) + 'L of beer per hour<br>';

    // Assign a color for each name.
    var nameToColor = {};
    for (var idx in drinkers) {
      nameToColor[drinkers[idx]] = "hsl(" + (360.0 * idx / drinkers.length) + ", 50%, 50%)";
    }

    function hsla(color, alpha) {
      if (color.indexOf('hsl(') === 0) {
        return color.replace('hsl(', 'hsla(').replace(')', ', ' + alpha + ')');
      }
      return color;
    }

    var ctx = document.getElementById('myChart').getContext('2d');

    datasets.forEach(function (item) {
        if (item.label === 'Total cumulative') {
            item.backgroundColor = 'rgba(0, 0, 0, 0.1)';
            item.borderColor = 'rgba(0, 0, 0, 0.7)';
            item.borderDash = [6, 4];
            item.pointRadius = 0;
            item.yAxisID = 'y1';
        } else if (item.label === 'Total speed') {
            item.backgroundColor = 'rgba(54, 162, 235, 0.1)';
            item.borderColor = 'rgba(54, 162, 235, 0.9)';
            item.pointRadius = 2;
            item.yAxisID = 'y2';
        } else {
            item.backgroundColor = nameToColor[item.label];
            item.borderColor = nameToColor[item.label];
            item.hoverBackgroundColor = nameToColor[item.label];
            item.hoverBorderColor = nameToColor[item.label];
            item.yAxisID = 'y';
        }
    });

    var chart = new Chart(ctx, {
        // The type of chart we want to create
        type: 'line',

        // The data for our dataset
        data: {
            labels: labels,
            datasets: datasets,
        },

        // Configuration options go here
        options: {
            elements: {
                line: {
                    fill: false,
                    tension: 0,
                },
            },
            scales: {
                x: {
                    type: 'category',
                    title: {
                        display: true,
                        text: 'Hour'
                    }
                },
                y: {
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Drinkers (L)'
                    }
                },
                y1: {
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Total cumulative (L)'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                },
                y2: {
                    position: 'right',
                    display: false,
                    grid: {
                        drawOnChartArea: false
                    }
                }
            },
            monotone: 'monotone',
            plugins: {
                peakHighlight: {
                    index: peakIndex,
                },
                tooltip: {
                    callbacks: {
                        afterFooter: function(tooltip) {
                            // Datasets are sorted by amount. First index
                            // is the winner.
                            var prizes = [
                                '\uD83E\uDD47', // gold
                                '\uD83E\uDD48', // silver
                                '\uD83E\uDD49', // bronze
                            ];
                            var text = '';
                            for (var i in tooltip) {
                                if (tooltip[i].datasetIndex < 3)
                                    text += prizes[tooltip[i].datasetIndex];
                            }
                            return text;
                        },
                    },
                    footerFontSize: 40,
                },
            },
        },
    });
}
