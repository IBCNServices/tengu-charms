#!/bin/bash
# storm-nimbus daemon
# chkconfig: 345 20 80
# description: storm daemon
# processname: storm
DAEMON_PATH="/opt/storm/apache-storm-%%%VERSION%%%/bin"
LOG_PATH="/opt/storm/apache-storm-%%%VERSION%%%/logs"
DAEMON=$DAEMON_PATH/storm

NAME=storm
DESC="Starts the Storm"
PIDFILE=$DAEMON_PATH/$NAME.pid
SCRIPTNAME=/etc/init.d/$NAME
UIPIDFILE=$DAEMON_PATH/storm-ui.pid
DRPCPIDFILE=$DAEMON_PATH/storm-drpc.pid
NIMBUS=nimbus
UI=ui
SUPERVISOR=supervisor
DRPC=drpc

case "$1" in
start)
	printf "%-50s" "Starting $NAME..."

	cd $DAEMON_PATH
	if [ -f /opt/storm/latest/conf/master ]; then
		daemon --respawn --name="storm-nimbus" --user=storm --pidfile=$PIDFILE -- $DAEMON $NIMBUS
		daemon --respawn --name="storm-ui" --user=storm  --pidfile=$UIPIDFILE -- $DAEMON $UI
	else
		daemon --respawn --name="storm-supervisor" --user=storm  --pidfile=$PIDFILE -- $DAEMON $SUPERVISOR
		daemon --respawn --name="storm-drpc" --user=storm  --pidfile=$DRPCPIDFILE -- $DAEMON $DRPC
	fi
	sleep 1
        if [ -f $PIDFILE ]; then
	    printf "%s\n" "Ok"
        else
            printf "%s\n" "Fail"
	    exit 1
        fi
;;
status)
        printf "%-50s" "Checking $NAME..."
        if [ -f $PIDFILE ]; then
            PID=`cat $PIDFILE`
            if [ -z "`ps axf | grep ${PID} | grep -v grep`" ]; then
                printf "%s\n" "Process dead but pidfile exists"
            else
                echo "Running"
            fi
        else
            printf "%s\n" "Service not running"
        fi
;;
stop)
        printf "%-50s" "Stopping $NAME"

            cd $DAEMON_PATH
        if [ -f $PIDFILE ]; then
	    if [ -f /opt/storm/latest/conf/master ]; then
            	daemon --pidfile=$PIDFILE --name="storm-nimbus"  --stop
	    else
            	daemon --pidfile=$PIDFILE --name="storm-supervisor"  --stop
	    fi
            printf "%s\n" "Ok"
            rm -f $PIDFILE
        else
            printf "%s\n" "pidfile not found"
        fi
        if [ -f $UIPIDFILE ]; then
            daemon --pidfile=$UIPIDFILE --name="storm-ui" --stop
            printf "%s\n" "Ok"
            rm -f $UIPIDFILE
	fi
        if [ -f $DRPCPIDFILE ]; then
            daemon --pidfile=$DRPCPIDFILE --name="storm-drpc" --stop
            printf "%s\n" "Ok"
            rm -f $DRPCPIDFILE
	fi
        sleep 5
        killall -9 java
;;

restart)
  	$0 stop
  	$0 start
;;

*)
        echo "Usage: $0 {status|start|stop|restart}"
        exit 1
esac
