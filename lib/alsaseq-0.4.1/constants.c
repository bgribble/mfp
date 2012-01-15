/*
    constants.c - ALSA sequencer bindings for Python

    Copyright (c) 2007 Patricio Paez <pp@pp.com.mx>

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>
*/

PyModule_AddIntConstant( m, "SND_SEQ_EVENT_SYSTEM", SND_SEQ_EVENT_SYSTEM );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_RESULT", SND_SEQ_EVENT_RESULT );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_NOTE", SND_SEQ_EVENT_NOTE );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_NOTEON", SND_SEQ_EVENT_NOTEON );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_NOTEOFF", SND_SEQ_EVENT_NOTEOFF );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_KEYPRESS", SND_SEQ_EVENT_KEYPRESS );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_CONTROLLER", SND_SEQ_EVENT_CONTROLLER );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_PGMCHANGE", SND_SEQ_EVENT_PGMCHANGE );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_CHANPRESS", SND_SEQ_EVENT_CHANPRESS );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_PITCHBEND", SND_SEQ_EVENT_PITCHBEND );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_CONTROL14", SND_SEQ_EVENT_CONTROL14 );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_NONREGPARAM", SND_SEQ_EVENT_NONREGPARAM );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_REGPARAM", SND_SEQ_EVENT_REGPARAM );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_SONGPOS", SND_SEQ_EVENT_SONGPOS );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_SONGSEL", SND_SEQ_EVENT_SONGSEL );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_QFRAME", SND_SEQ_EVENT_QFRAME );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_TIMESIGN", SND_SEQ_EVENT_TIMESIGN );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_KEYSIGN", SND_SEQ_EVENT_KEYSIGN );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_START", SND_SEQ_EVENT_START );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_CONTINUE", SND_SEQ_EVENT_CONTINUE );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_STOP", SND_SEQ_EVENT_STOP );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_SETPOS_TICK", SND_SEQ_EVENT_SETPOS_TICK );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_SETPOS_TIME", SND_SEQ_EVENT_SETPOS_TIME );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_TEMPO", SND_SEQ_EVENT_TEMPO );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_CLOCK", SND_SEQ_EVENT_CLOCK );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_TICK", SND_SEQ_EVENT_TICK );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_QUEUE_SKEW", SND_SEQ_EVENT_QUEUE_SKEW );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_SYNC_POS", SND_SEQ_EVENT_SYNC_POS );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_TUNE_REQUEST", SND_SEQ_EVENT_TUNE_REQUEST );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_RESET", SND_SEQ_EVENT_RESET );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_SENSING", SND_SEQ_EVENT_SENSING );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_ECHO", SND_SEQ_EVENT_ECHO );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_OSS", SND_SEQ_EVENT_OSS );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_CLIENT_START", SND_SEQ_EVENT_CLIENT_START );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_CLIENT_EXIT", SND_SEQ_EVENT_CLIENT_EXIT );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_CLIENT_CHANGE", SND_SEQ_EVENT_CLIENT_CHANGE );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_PORT_START", SND_SEQ_EVENT_PORT_START );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_PORT_EXIT", SND_SEQ_EVENT_PORT_EXIT );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_PORT_CHANGE", SND_SEQ_EVENT_PORT_CHANGE );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_PORT_SUBSCRIBED", SND_SEQ_EVENT_PORT_SUBSCRIBED );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_PORT_UNSUBSCRIBED", SND_SEQ_EVENT_PORT_UNSUBSCRIBED );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_USR0", SND_SEQ_EVENT_USR0 );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_USR1", SND_SEQ_EVENT_USR1 );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_USR2", SND_SEQ_EVENT_USR2 );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_USR3", SND_SEQ_EVENT_USR3 );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_USR4", SND_SEQ_EVENT_USR4 );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_USR5", SND_SEQ_EVENT_USR5 );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_USR6", SND_SEQ_EVENT_USR6 );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_USR7", SND_SEQ_EVENT_USR7 );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_USR8", SND_SEQ_EVENT_USR8 );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_USR9", SND_SEQ_EVENT_USR9 );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_SYSEX", SND_SEQ_EVENT_SYSEX );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_BOUNCE", SND_SEQ_EVENT_BOUNCE );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_USR_VAR0", SND_SEQ_EVENT_USR_VAR0 );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_USR_VAR1", SND_SEQ_EVENT_USR_VAR1 );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_USR_VAR2", SND_SEQ_EVENT_USR_VAR2 );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_USR_VAR3", SND_SEQ_EVENT_USR_VAR3 );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_USR_VAR4", SND_SEQ_EVENT_USR_VAR4 );
PyModule_AddIntConstant( m, "SND_SEQ_EVENT_NONE", SND_SEQ_EVENT_NONE );

PyModule_AddIntConstant( m, "SND_SEQ_TIME_STAMP_REAL", SND_SEQ_TIME_STAMP_REAL );
