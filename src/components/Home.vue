<template>
    <div id='vuewrapper' style="height: 100%;">
        <template v-if="state.mapLoading || state.plotLoading">
            <div id="waiting">
                <atom-spinner
                    :animation-duration="1000"
                    :color="'#64e9ff'"
                    :size="300"
                />
            </div>
        </template>
        <TxInputs fixed-aspect-ratio v-if="state.mapAvailable && state.showMap && state.showRadio"></TxInputs>
        <ParamViewer    @close="state.showParams = false" v-if="state.showParams"></ParamViewer>
        <MessageViewer  @close="state.showMessages = false" v-if="state.showMessages"></MessageViewer>
        <DeviceIDViewer @close="state.showDeviceIDs = false" v-if="state.showDeviceIDs"></DeviceIDViewer>
        <AttitudeViewer @close="state.showAttitude = false" v-if="state.showAttitude"></AttitudeViewer>
        <MagFitTool     @close="state.showMagfit = false" v-if="state.showMagfit"></MagFitTool>
        <EkfHelperTool  @close="state.showEkfHelper = false" v-if="state.showEkfHelper"></EkfHelperTool>
        <div class="container-fluid" style="height: 100%; overflow: hidden;">

            <sidebar/>

            <main class="col-md-9 ml-sm-auto col-lg-10 flex-column d-sm-flex" role="main">

                <div class="row"
                     v-bind:class="[state.showMap ? 'h-50' : 'h-100']"
                     v-if="state.plotOn">
                    <div class="col-12">
                        <Plotly/>
                    </div>
                </div>
                <div class="row" v-bind:class="[state.plotOn ? 'h-50' : 'h-100']"
                     v-if="state.mapAvailable && mapOk && state.showMap">
                    <div class="col-12 noPadding">
                        <CesiumViewer ref="cesiumViewer"/>
                    </div>
                </div>

                <div style="position: absolute; bottom: 20px; right: 20px; z-index: 9999;">
                    <Chatbot />
                </div>
            </main>

        </div>
    </div>
</template>

<script>
import isOnline from 'is-online'
import Plotly from '@/components/Plotly.vue'
import CesiumViewer from '@/components/CesiumViewer.vue'
import Sidebar from '@/components/Sidebar.vue'
import TxInputs from '@/components/widgets/TxInputs.vue'
import ParamViewer from '@/components/widgets/ParamViewer.vue'
import MessageViewer from '@/components/widgets/MessageViewer.vue'
import DeviceIDViewer from '@/components/widgets/DeviceIDViewer.vue'
import AttitudeViewer from '@/components/widgets/AttitudeWidget.vue'
import { AtomSpinner } from 'epic-spinners'
import { Color } from 'cesium'
import colormap from 'colormap'
import { DataflashDataExtractor } from '../tools/dataflashDataExtractor'
import { MavlinkDataExtractor } from '../tools/mavlinkDataExtractor'
import { DjiDataExtractor } from '../tools/djiDataExtractor'
import MagFitTool from '@/components/widgets/MagFitTool.vue'
import EkfHelperTool from '@/components/widgets/EkfHelperTool.vue'
import Vue from 'vue'
import Chatbot from './Chatbot.vue'
import { store } from '@/components/Globals.js'

export default {
    name: 'Home',
    components: {
        Sidebar,
        Plotly,
        CesiumViewer,
        AtomSpinner,
        TxInputs,
        ParamViewer,
        MessageViewer,
        DeviceIDViewer,
        AttitudeViewer,
        MagFitTool,
        EkfHelperTool,
        Chatbot
    },
    data () {
        return {
            state: store,
            dataExtractor: null
        }
    },

    created () {
        this.$eventHub.$on('messagesDoneLoading', this.extractFlightData)
        this.state.messages = {}
        this.state.timeAttitude = []
        this.state.timeAttitudeQ = []
        this.state.currentTrajectory = []
        isOnline().then(a => { this.state.isOnline = a })
    },
    beforeDestroy () {
        this.$eventHub.$off('messages')
    },
    methods: {

        extractFlightData () {
            if (!this.state.messages || typeof this.state.messages !== 'object') {
                console.error('Invalid message data')
                return
            }

            if (this.dataExtractor === null) {
                if (this.state.logType === 'tlog') {
                    this.dataExtractor = MavlinkDataExtractor
                } else if (this.state.logType === 'dji') {
                    this.dataExtractor = DjiDataExtractor
                } else {
                    this.dataExtractor = DataflashDataExtractor
                }
            }

            // Safe check on FMTU
            if (
              this.state.messages &&
              'FMTU' in this.state.messages &&
              Array.isArray(this.state.messages.FMTU)
            ) {
              if (this.state.messages.FMTU.length === 0) {
                this.state.processStatus = 'ERROR PARSING?'
              } else {
                try {
                    const fmt = this.state.messages.FMTU?.[0]
                    if (fmt?.FmtType) {
                        console.log('Format Type:', fmt.FmtType)
                    }
                    } catch (e) {
                        console.warn('Failed to extract FMTU format type:', e)
                    }
                }
            } else {
              console.warn('FMTU message missing or malformed')
            }
            if ('FMTU' in this.state.messages && Array.isArray(this.state.messages.FMTU) && this.state.messages.FMTU.length === 0) {
                this.state.processStatus = 'ERROR PARSING?'
            }

            if (this.state.flightModeChanges.length === 0) {
                this.state.flightModeChanges = this.dataExtractor.extractFlightModes(this.state.messages)
            }
            Vue.delete(this.state.messages, 'MODE')

            if (this.state.events.length === 0) {
                this.state.events = this.dataExtractor.extractEvents(this.state.messages)
            }
            Vue.delete(this.state.messages, 'STAT')
            Vue.delete(this.state.messages, 'EV')

            if (this.state.mission.length === 0) {
                this.state.mission = this.dataExtractor.extractMission(this.state.messages)
            }
            Vue.delete(this.state.messages, 'CMD')

            this.state.vehicle = this.dataExtractor.extractVehicleType(this.state.messages)

            if (!this.state.params) {
                this.state.params = this.dataExtractor.extractParams(this.state.messages)
                if (this.state.params) {
                    this.state.defaultParams = this.dataExtractor.extractDefaultParams(this.state.messages)
                    this.$eventHub.$on('cesium-time-changed', (time) => {
                        this.state.params.seek(time)
                    })
                }
            }

            if (this.state.vehicle === 'quadcopter') {
                const frameType = this.state.params?.get('FRAME_TYPE')
                if (frameType === 0) {
                    this.state.vehicle += '+'
                } else {
                    this.state.vehicle += 'x'
                }
            }

            if (this.state.textMessages.length === 0) {
                this.state.textMessages = this.dataExtractor.extractTextMessages(this.state.messages)
            }
            Vue.delete(this.state.messages, 'MSG')

            if (this.state.colors.length === 0) {
                this.generateColorMMap()
            }

            this.state.attitudeSources = this.dataExtractor.extractAttitudeSources(this.state.messages)

            if (this.state.attitudeSources.quaternions.length > 0) {
                const source = this.state.attitudeSources.quaternions[0]
                this.state.attitudeSource = source
                this.state.timeAttitudeQ = this.dataExtractor.extractAttitudeQ(this.state.messages, source)
            } else if (this.state.attitudeSources.eulers.length > 0) {
                const source = this.state.attitudeSources.eulers[0]
                this.state.attitudeSource = source
                this.state.timeAttitude = this.dataExtractor.extractAttitude(this.state.messages, source)
            }

            const list = Object.keys(this.state.timeAttitude)
            this.state.lastTime = parseInt(list[list.length - 1] || 0)

            this.state.trajectorySources = this.dataExtractor.extractTrajectorySources(this.state.messages)
            if (this.state.trajectorySources.length > 0) {
                const first = this.state.trajectorySources[0]
                this.state.trajectorySource = first
                this.state.trajectories = this.dataExtractor.extractTrajectory(this.state.messages, first)
                try {
                    this.state.currentTrajectory = this.state.trajectories[first].trajectory
                    this.state.timeTrajectory = this.state.trajectories[first].timeTrajectory
                } catch (err) {
                    console.warn('Unable to load trajectory:', err)
                }
            }

            try {
                const gps = this.state.messages.GPS || this.state.messages['GPS[0]']
                if (gps) {
                    this.state.metadata = {
                        startTime: this.dataExtractor.extractStartTime(gps)
                    }
                }
            } catch (error) {
                console.warn('Unable to load metadata:', error)
            }

            try {
                this.state.namedFloats = this.dataExtractor.extractNamedValueFloatNames(this.state.messages)
                console.log(this.state.namedFloats)
            } catch (error) {
                console.warn('Unable to load named floats:', error)
            }

            Vue.delete(this.state.messages, 'AHR2')
            Vue.delete(this.state.messages, 'POS')
            Vue.delete(this.state.messages, 'GPS')

            this.state.fences = this.dataExtractor.extractFences(this.state.messages)

            this.state.processStatus = 'Processed!'
            this.state.processDone = true

            setTimeout(() => {
                this.$eventHub.$emit('set-selected', 'plot')
            }, 2000)

            if (!this.state.mapAvailable) {
                this.state.mapAvailable = this.state.currentTrajectory.length > 0
                if (this.state.mapAvailable) {
                    this.state.showMap = true
                }
            }
        },

        generateColorMMap () {
            const colorMapOptions = {
                colormap: 'hsv',
                nshades: Math.max(11, this.setOfModes.length),
                format: 'rgbaString',
                alpha: 1
            }
            this.state.cssColors = colormap(colorMapOptions)

            colorMapOptions.format = 'float'
            this.state.colors = []
            for (const rgba of colormap(colorMapOptions)) {
                this.state.colors.push(new Color(rgba[0], rgba[1], rgba[2]))
            }
        }
    },
    computed: {
        mapOk () {
            return (
                this.state.flightModeChanges?.length > 0 &&
                this.state.currentTrajectory?.length > 0 &&
                (Object.keys(this.state.timeAttitude).length > 0 ||
                    Object.keys(this.state.timeAttitudeQ).length > 0)
            )
        },
        setOfModes () {
            const set = []
            if (!this.state.flightModeChanges) return []
            for (const mode of this.state.flightModeChanges) {
                if (!set.includes(mode[1])) set.push(mode[1])
            }
            return set
        }
    }
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>

    .nav-side-menu ul :not(collapsed) .arrow:before,
    .nav-side-menu li :not(collapsed) .arrow:before {
        font-family: 'Montserrat', sans-serif;
        content: "\f078";
        display: inline-block;
        padding-left: 10px;
        padding-right: 10px;
        vertical-align: middle;
        float: right;
    }

    body {
        margin: 0;
        padding: 0;
    }

    .container-fluid {
        padding-left: 0;
        padding-right: 0;
    }

    div .col-12 {
        padding-left: 0;
        padding-right: 0;
    }

    i {
        margin: 10px;
    }

    i .dropdown {
        float: right;
    }

    .noPadding {
        padding-left: 4px;
        padding-right: 6px;
        max-height: 100%;
    }

    div #waiting {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 1000;
        display: block;
        background-color: black;
        opacity: 0.75;
        text-align: center;
    }
    /* ATOM SPINNER */

      div .atom-spinner {
        margin: auto;
        margin-top: 15%;
    }

</style>
<style>
a {
    color: #ffffff !important;
}
</style>
