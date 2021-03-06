# Copyright (C) 2018 British Broadcasting Corporation
#
# Modifications Copyright 2018 Riedel Communications GmbH & Co. KG
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from time import sleep
import socket
import uuid
import json

from zeroconf_monkey import ServiceBrowser, Zeroconf
from MdnsListener import MdnsListener
from TestResult import Test
from GenericTest import GenericTest, test_depends
from IS04Utils import IS04Utils

REG_API_KEY = "registration"
QUERY_API_KEY = "query"


class IS0402Test(GenericTest):
    """
    Runs IS-04-02-Test
    """
    def __init__(self, apis):
        # Don't auto-test /health/nodes/{nodeId} as it's impossible to automatically gather test data
        omit_paths = [
          "/health/nodes/{nodeId}"
        ]
        GenericTest.__init__(self, apis, omit_paths)
        self.reg_url = self.apis[REG_API_KEY]["url"]
        self.query_url = self.apis[QUERY_API_KEY]["url"]
        self.zc = None
        self.is04_reg_utils = IS04Utils(self.reg_url)
        self.is04_query_utils = IS04Utils(self.query_url)

    def set_up_tests(self):
        self.zc = Zeroconf()
        self.zc_listener = MdnsListener(self.zc)

    def tear_down_tests(self):
        if self.zc:
            self.zc.close()
            self.zc = None

    def test_01(self):
        """Registration API advertises correctly via mDNS"""

        test = Test("Registration API advertises correctly via mDNS")

        browser = ServiceBrowser(self.zc, "_nmos-registration._tcp.local.", self.zc_listener)
        sleep(2)
        serv_list = self.zc_listener.get_service_list()
        for api in serv_list:
            address = socket.inet_ntoa(api.address)
            port = api.port
            if address in self.reg_url and ":{}".format(port) in self.reg_url:
                properties = self.convert_bytes(api.properties)
                if "pri" not in properties:
                    return test.FAIL("No 'pri' TXT record found in Registration API advertisement.")
                try:
                    priority = int(properties["pri"])
                    if priority < 0:
                        return test.FAIL("Priority ('pri') TXT record must be greater than zero.")
                    elif priority >= 100:
                        return test.FAIL("Priority ('pri') TXT record must be less than 100 for a production instance.")
                except Exception as e:
                    return test.FAIL("Priority ('pri') TXT record is not an integer.")

                # Other TXT records only came in for IS-04 v1.1+
                api = self.apis[REG_API_KEY]
                if self.is04_reg_utils.compare_api_version(api["version"], "v1.1") >= 0:
                    if "api_ver" not in properties:
                        return test.FAIL("No 'api_ver' TXT record found in Registration API advertisement.")
                    elif api["version"] not in properties["api_ver"].split(","):
                        return test.FAIL("Registry does not claim to support version under test.")

                    if "api_proto" not in properties:
                        return test.FAIL("No 'api_proto' TXT record found in Registration API advertisement.")
                    elif properties["api_proto"] != "http":
                        return test.FAIL("API protocol is not advertised as 'http'. "
                                         "This test suite does not currently support 'https'.")

                return test.PASS()
        return test.FAIL("No matching mDNS announcement found for Registration API.")

    def test_02(self):
        """Query API advertises correctly via mDNS"""

        test = Test("Query API advertises correctly via mDNS")

        browser = ServiceBrowser(self.zc, "_nmos-query._tcp.local.", self.zc_listener)
        sleep(2)
        serv_list = self.zc_listener.get_service_list()
        for api in serv_list:
            address = socket.inet_ntoa(api.address)
            port = api.port
            if address in self.query_url and ":{}".format(port) in self.query_url:
                properties = self.convert_bytes(api.properties)
                if "pri" not in properties:
                    return test.FAIL("No 'pri' TXT record found in Query API advertisement.")
                try:
                    priority = int(properties["pri"])
                    if priority < 0:
                        return test.FAIL("Priority ('pri') TXT record must be greater than zero.")
                    elif priority >= 100:
                        return test.FAIL("Priority ('pri') TXT record must be less than 100 for a production instance.")
                except Exception as e:
                    return test.FAIL("Priority ('pri') TXT record is not an integer.")

                # Other TXT records only came in for IS-04 v1.1+
                api = self.apis[QUERY_API_KEY]
                if self.is04_query_utils.compare_api_version(api["version"], "v1.1") >= 0:
                    if "api_ver" not in properties:
                        return test.FAIL("No 'api_ver' TXT record found in Query API advertisement.")
                    elif api["version"] not in properties["api_ver"].split(","):
                        return test.FAIL("Registry does not claim to support version under test.")

                    if "api_proto" not in properties:
                        return test.FAIL("No 'api_proto' TXT record found in Query API advertisement.")
                    elif properties["api_proto"] != "http":
                        return test.FAIL("API protocol is not advertised as 'http'. "
                                         "This test suite does not currently support 'https'.")

                return test.PASS()
        return test.FAIL("No matching mDNS announcement found for Query API.")

    def test_03(self):
        """Registration API accepts and stores a valid Node resource"""

        test = Test("Registration API accepts and stores a valid Node resource")

        api = self.apis[REG_API_KEY]
        if self.is04_reg_utils.compare_api_version(api["version"], "v2.0") <= 0:
            with open("test_data/IS0402/v1.2_node.json") as node_data:
                node_json = json.load(node_data)
                if self.is04_reg_utils.compare_api_version(api["version"], "v1.2") < 0:
                    node_json = self.downgrade_resource("node", node_json, self.apis[REG_API_KEY]["version"])

                valid, r = self.do_request("POST", self.reg_url + "resource", data={"type": "node", "data": node_json})

                if not valid:
                    return test.FAIL("Registration API did not respond as expected")
                elif r.status_code == 201:
                    return test.PASS()
                else:
                    return test.FAIL("Registration API returned an unexpected response: {} {}".format(r.status_code, r.text))
        else:
            return test.FAIL("Version > 1 not supported yet.")

        return test.FAIL("An unknown error occurred")

    def test_04(self):
        """Registration API rejects an invalid Node resource with a 400 HTTP code"""

        test = Test("Registration API rejects an invalid Node resource with a 400 HTTP code")

        bad_json = {"notanode": True}
        return self.do_400_check(test, "node", bad_json)

    @test_depends
    def test_05(self):
        """Registration API accepts and stores a valid Device resource"""

        test = Test("Registration API accepts and stores a valid Device resource")

        api = self.apis[REG_API_KEY]
        if self.is04_reg_utils.compare_api_version(api["version"], "v2.0") <= 0:
            with open("test_data/IS0402/v1.2_device.json") as device_data:

                device_json = json.load(device_data)

                if self.is04_reg_utils.compare_api_version(api["version"], "v1.2") < 0:
                    device_json = self.downgrade_resource("device", device_json, self.apis[REG_API_KEY]["version"])

                valid, r = self.do_request("POST", self.reg_url + "resource", data={"type": "device",
                                                                                    "data": device_json})

                if not valid:
                    return test.FAIL("Registration API did not respond as expected")
                elif r.status_code == 201:
                    return test.PASS()
                else:
                    return test.FAIL("Registration API returned an unexpected response: {} {}".format(r.status_code,
                                                                                                      r.text))
        else:
            return test.FAIL("Version > 1 not supported yet.")

        return test.FAIL("An unknown error occurred")

    @test_depends
    def test_06(self):
        """Registration API rejects an invalid Device resource with a 400 HTTP code"""

        test = Test("Registration API rejects an invalid Device resource with a 400 HTTP code")

        bad_json = {"notadevice": True}
        return self.do_400_check(test, "device", bad_json)

    @test_depends
    def test_07(self):
        """Registration API accepts and stores a valid Source resource"""

        test = Test("Registration API accepts and stores a valid Source resource")

        api = self.apis[REG_API_KEY]
        if self.is04_reg_utils.compare_api_version(api["version"], "v2.0") <= 0:
            with open("test_data/IS0402/v1.2_source.json") as source_data:
                source_json = json.load(source_data)
                if self.is04_reg_utils.compare_api_version(api["version"], "v1.2") < 0:
                    source_json = self.downgrade_resource("source", source_json, self.apis[REG_API_KEY]["version"])

                valid, r = self.do_request("POST", self.reg_url + "resource", data={"type": "source",
                                                                                    "data": source_json})

                if not valid:
                    return test.FAIL("Registration API did not respond as expected")
                elif r.status_code == 201:
                    return test.PASS()
                else:
                    return test.FAIL("Registration API returned an unexpected response: {} {}".format(r.status_code, r.text))
        else:
            return test.FAIL("Version > 1 not supported yet.")

        return test.FAIL("An unknown error occurred")

    @test_depends
    def test_08(self):
        """Registration API rejects an invalid Source resource with a 400 HTTP code"""

        test = Test("Registration API rejects an invalid Source resource with a 400 HTTP code")

        bad_json = {"notasource": True}
        return self.do_400_check(test, "source", bad_json)

    @test_depends
    def test_09(self):
        """Registration API accepts and stores a valid Flow resource"""

        test = Test("Registration API accepts and stores a valid Flow resource")

        api = self.apis[REG_API_KEY]
        if self.is04_reg_utils.compare_api_version(api["version"], "v2.0") <= 0:
            with open("test_data/IS0402/v1.2_flow.json") as flow_data:
                flow_json = json.load(flow_data)

                if self.is04_reg_utils.compare_api_version(api["version"], "v1.2") < 0:
                    flow_json = self.downgrade_resource("flow", flow_json, self.apis[REG_API_KEY]["version"])
                valid, r = self.do_request("POST", self.reg_url + "resource", data={"type": "flow",
                                                                                    "data": flow_json})

                if not valid:
                    return test.FAIL("Registration API did not respond as expected")
                elif r.status_code == 201:
                    return test.PASS()
                else:
                    return test.FAIL("Registration API returned an unexpected response: {} {}".format(r.status_code, r.text))
        else:
            return test.FAIL("Version > 1 not supported yet.")

        return test.FAIL("An unknown error occurred")

    @test_depends
    def test_10(self):
        """Registration API rejects an invalid Flow resource with a 400 HTTP code"""

        test = Test("Registration API rejects an invalid Flow resource with a 400 HTTP code")

        bad_json = {"notaflow": True}
        return self.do_400_check(test, "flow", bad_json)

    @test_depends
    def test_11(self):
        """Registration API accepts and stores a valid Sender resource"""

        test = Test("Registration API accepts and stores a valid Sender resource")

        api = self.apis[REG_API_KEY]
        if self.is04_reg_utils.compare_api_version(api["version"], "v2.0") <= 0:
            with open("test_data/IS0402/v1.2_sender.json") as sender_data:
                sender_json = json.load(sender_data)
                if self.is04_reg_utils.compare_api_version(api["version"], "v1.2") < 0:
                    sender_json = self.downgrade_resource("sender", sender_json, self.apis[REG_API_KEY]["version"])
                valid, r = self.do_request("POST", self.reg_url + "resource", data={"type": "sender",
                                                                                    "data": sender_json})

                if not valid:
                    return test.FAIL("Registration API did not respond as expected")
                elif r.status_code == 201:
                    return test.PASS()
                else:
                    return test.FAIL("Registration API returned an unexpected response: {} {}".format(r.status_code, r.text))
        else:
            return test.FAIL("Version > 1 not supported yet.")

        return test.FAIL("An unknown error occurred")

    @test_depends
    def test_12(self):
        """Registration API rejects an invalid Sender resource with a 400 HTTP code"""

        test = Test("Registration API rejects an invalid Sender resource with a 400 HTTP code")

        bad_json = {"notasender": True}
        return self.do_400_check(test, "sender", bad_json)

    @test_depends
    def test_13(self):
        """Registration API accepts and stores a valid Receiver resource"""

        test = Test("Registration API accepts and stores a valid Receiver resource")

        api = self.apis[REG_API_KEY]
        if self.is04_reg_utils.compare_api_version(api["version"], "v2.0") <= 0:
            with open("test_data/IS0402/v1.2_receiver.json") as receiver_data:
                receiver_json = json.load(receiver_data)
                if self.is04_reg_utils.compare_api_version(api["version"], "v1.2") < 0:
                    receiver_json = self.downgrade_resource("receiver", receiver_json, self.apis[REG_API_KEY]["version"])
                valid, r = self.do_request("POST", self.reg_url + "resource", data={"type": "receiver",
                                                                                    "data": receiver_json})

                if not valid:
                    return test.FAIL("Registration API did not respond as expected")
                elif r.status_code == 201:
                    return test.PASS()
                else:
                    return test.FAIL("Registration API returned an unexpected response: {} {}".format(r.status_code, r.text))
        else:
            return test.FAIL("Version > 1 not supported yet.")

        return test.FAIL("An unknown error occurred")

    @test_depends
    def test_14(self):
        """Registration API rejects an invalid Receiver resource with a 400 HTTP code"""

        test = Test("Registration API rejects an invalid Receiver resource with a 400 HTTP code")

        bad_json = {"notareceiver": True}
        return self.do_400_check(test, "receiver", bad_json)

    def test_15(self):
        """Query API implements pagination"""

        test = Test("Query API implements pagination")

        if self.apis[QUERY_API_KEY]["version"] == "v1.0":
            return test.NA("This test does not apply to v1.0")

        return test.MANUAL()

    def test_16(self):
        """Query API implements downgrade queries"""

        test = Test("Query API implements downgrade queries")

        if self.apis[QUERY_API_KEY]["version"] == "v1.0":
            return test.NA("This test does not apply to v1.0")

        return test.MANUAL()

    def test_17(self):
        """Query API implements basic query parameters"""

        test = Test("Query API implements basic query parameters")

        try:
            valid, r = self.do_request("GET", self.query_url + "nodes")
            if not valid:
                return test.FAIL("Query API failed to respond to query")
            elif len(r.json()) == 0:
                return test.NA("No Nodes found in registry. Test cannot proceed.")
        except json.decoder.JSONDecodeError:
            return test.FAIL("Non-JSON response returned")

        random_label = uuid.uuid4()
        query_string = "?label=" + str(random_label)
        valid, r = self.do_request("GET", self.query_url + "nodes" + query_string)
        if not valid:
            return test.FAIL("Query API failed to respond to query")
        elif len(r.json()) > 0:
            return test.FAIL("Query API returned more records than expected for query: {}".format(query_string))

        return test.PASS()

    def test_18(self):
        """Query API implements RQL"""

        test = Test("Query API implements RQL")

        if self.apis[QUERY_API_KEY]["version"] == "v1.0":
            return test.NA("This test does not apply to v1.0")

        try:
            valid, r = self.do_request("GET", self.query_url + "nodes")
            if not valid:
                return test.FAIL("Query API failed to respond to query")
            elif len(r.json()) == 0:
                return test.NA("No Nodes found in registry. Test cannot proceed.")
        except json.decoder.JSONDecodeError:
            return test.FAIL("Non-JSON response returned")

        random_label = uuid.uuid4()
        query_string = "?query.rql=eq(label," + str(random_label) + ")"
        valid, r = self.do_request("GET", self.query_url + "nodes" + query_string)
        if not valid:
            return test.FAIL("Query API failed to respond to query")
        elif r.status_code == 501:
            return test.NA("Query API signalled that it does not support RQL queries")
        elif len(r.json()) > 0:
            return test.FAIL("Query API returned more records than expected for query: {}".format(query_string))

        return test.PASS()

    def test_19(self):
        """Query API implements ancestry queries"""

        test = Test("Query API implements ancestry queries")

        if self.apis[QUERY_API_KEY]["version"] == "v1.0":
            return test.NA("This test does not apply to v1.0")

        try:
            valid, r = self.do_request("GET", self.query_url + "sources")
            if not valid:
                return test.FAIL("Query API failed to respond to query")
            elif len(r.json()) == 0:
                return test.NA("No Sources found in registry. Test cannot proceed.")
        except json.decoder.JSONDecodeError:
            return test.FAIL("Non-JSON response returned")

        random_label = uuid.uuid4()
        query_string = "?query.ancestry_id=" + str(random_label) + "&query.ancestry_type=children"
        valid, r = self.do_request("GET", self.query_url + "sources" + query_string)
        if not valid:
            return test.FAIL("Query API failed to respond to query")
        elif r.status_code == 501:
            return test.NA("Query API signalled that it does not support ancestry queries")
        elif len(r.json()) > 0:
            return test.FAIL("Query API returned more records than expected for query: {}".format(query_string))

        return test.PASS()

    def do_400_check(self, test, resource_type, data):
        valid, r = self.do_request("POST", self.reg_url + "resource", data={"type": resource_type, "data": data})

        if not valid:
            return test.FAIL(r)

        if r.status_code != 400:
            return test.FAIL("Registration API returned a {} code for an invalid registration".format(r.status_code))

        schema = self.get_schema(REG_API_KEY, "POST", "/resource", 400)
        valid, message = self.check_response(REG_API_KEY, schema, "POST", r)

        if valid:
            return test.PASS()
        else:
            return test.FAIL(message)

    def downgrade_resource(self, resource_type, data, requested_version):
        """Downgrades given resource data to requested version"""
        version_major, version_minor = [int(x) for x in requested_version[1:].split(".")]

        if version_major == 1:
            if resource_type == "node":
                if version_minor <= 1:
                    keys_to_remove = [
                        "interfaces"
                    ]
                    for key in keys_to_remove:
                        if key in data:
                            del data[key]
                if version_minor == 0:
                    keys_to_remove = [
                        "api",
                        "clocks",
                        "description",
                        "tags"
                    ]
                    for key in keys_to_remove:
                        if key in data:
                            del data[key]
                return data

            elif resource_type == "device":
                if version_minor <= 1:
                    pass
                if version_minor == 0:
                    keys_to_remove = [
                        "controls",
                        "description",
                        "tags"
                    ]
                    for key in keys_to_remove:
                        if key in data:
                            del data[key]
                return data

            elif resource_type == "sender":
                if version_minor <= 1:
                    keys_to_remove = [
                        "caps",
                        "interface_bindings",
                        "subscription"
                    ]
                    for key in keys_to_remove:
                        if key in data:
                            del data[key]
                if version_minor == 0:
                    pass
                return data

            elif resource_type == "receiver":
                if version_minor <= 1:
                    keys_to_remove = [
                        "interface_bindings"
                    ]
                    for key in keys_to_remove:
                        if key in data:
                            del data[key]
                    if "subscription" in data and "active" in data["subscription"]:
                        del data["subscription"]["active"]
                if version_minor == 0:
                    pass
                return data

            elif resource_type == "source":
                if version_minor <= 1:
                    pass
                if version_minor == 0:
                    keys_to_remove = [
                        "channels",
                        "clock_name",
                        "grain_rate"
                    ]
                    for key in keys_to_remove:
                        if key in data:
                            del data[key]
                return data

            elif resource_type == "flow":
                if version_minor <= 1:
                    pass
                if version_minor == 0:
                    keys_to_remove = [
                        "bit_depth",
                        "colorspace",
                        "components",
                        "device_id",
                        "DID_SDID",
                        "frame_height",
                        "frame_width",
                        "grain_rate",
                        "interlace_mode",
                        "media_type",
                        "sample_rate",
                        "transfer_characteristic"
                    ]
                    for key in keys_to_remove:
                        if key in data:
                            del data[key]
                return data

        # Invalid request
        return None
