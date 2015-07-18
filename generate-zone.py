#!/usr/bin/env python2
import jsonrpclib, json, re, socket, ConfigParser

def is_valid_ipv4(ip_addr):
	try:
		socket.inet_pton(socket.AF_INET, ip_addr)
		return True
	except:
		return False

def is_valid_ipv6(ip_addr):
	try:
		socket.inet_pton(socket.AF_INET6, ip_addr)
		return True
	except:
		return False

def is_valid_domain(name):
	if re.match('^([a-zA-Z0-9._-]+\.)*[a-zA-Z0-9._-]+\.?$', name) and len(name) < 64 and isalnum(name[:1]):
		return True
	else:
		return False

def is_valid_txt(txt):
	if len(txt) < 255:
		return True
	else:
		return False
	
def make_list(input_data):
	if type(input_data) is list:
		return input_data
	else:
		return [input_data]

def make_fqdn(name):
	if name[-1] != '.':
		name += '.'
	return name

def get_names(rpc_server):
	rpc = jsonrpclib.Server(rpc_server)
	names = []

	for name in rpc.name_filter('^d/[a-z0-9_-]+$', 0):
		if not 'expired' in name:
			try:
				name_data = {'name': name['name'][2:], 'json': json.loads(name['value'])}
				names.append(name_data)
			except ValueError:
				pass

	block = rpc.getinfo()['blocks']

	return {'names': names, 'block': block}

class ProcessJSON(object):
	def __init__(self, domain, name_json):
		self.cname = []
		self.others = []
		self.imports = []

		if is_valid_domain(domain):
			self.process_name(domain, name_json)

	def process_name(self, domain, name_json):
		try:
			for record_type, values in name_json.items():
				if record_type == 'alias':
					for target in make_list(values):
						if is_valid_domain(target):
							self.cname.append({'type': 'cname', 'domain': domain, 'target': make_fqdn(target)})
				elif record_type == 'ip':
					for target in make_list(values):
						if is_valid_ipv4(target):
							self.others.append({'type': 'a', 'domain': domain, 'target': target})
				elif record_type == 'ip6':
					for target in make_list(values):
						if is_valid_ipv6(target):
							self.others.append({'type': 'aaaa', 'domain': domain, 'target': target})
				elif record_type == 'ns':
					for target in make_list(values):
						if is_valid_domain(target) and not is_valid_ipv4(target) and not is_valid_ipv6(target) and domain[:1] != "*":
							self.others.append({'type': 'ns', 'domain': domain, 'target': make_fqdn(target)})
				elif record_type == 'translate':
					for target in make_list(values):
						if is_valid_domain(target):
							self.others.append({'type': 'dname', 'domain': domain, 'target': make_fqdn(target)})
				elif record_type == 'info':
					for target in make_list(values):
						if(is_valid_txt(target)):
							self.others.append({'type': 'txt', 'domain': domain, 'target': json.dumps(target).replace('"', '\\"').encode('ascii', 'ignore')})
				elif record_type == 'map':
					for subdomain, value in values.items():
						if subdomain:
							newdomain = subdomain + '.' + domain
						else:
							newdomain = domain
						# If value is simply and IPv4/6 address, the domain is probably using the old v1 spec.
						if is_valid_ipv4(value):
							value = { "ip": [value] }
						elif is_valid_ipv6(value):
							value = { "ip6": [value] }
						if is_valid_domain(newdomain):
							self.process_name(newdomain, value)
				elif record_type == 'import':
					if type(values) == list:
						for value in values:
							if len(value) == 1:
								self.imports.append({'import': value, 'domain': domain})
							elif len(value) > 1:
								self.imports.append({'import': value[0], 'domain': value[1]+'.'+domain})
					elif type(values) == str:
						self.imports.append({'import': values, 'domain': domain})
		except AttributeError:
			pass

def generate_zone(names):
	cname_list = []
	for name in names:
		if name['json']:
			records = ProcessJSON(name['name'], name['json'])

			for record in records.cname:
				if record['domain'] not in cname_list:
					cname_list.append(record['domain'])
					yield record['domain'] + ' IN CNAME ' + record['target']

			for record in records.others:
				if record['type'] == 'a':
					if record['domain'] not in cname_list:
						yield record['domain'] + ' IN A ' + record['target']
				if record['type'] == 'aaaa':
					if record['domain'] not in cname_list:
						yield record['domain'] + ' IN AAAA ' + record['target']
				if record['type'] == 'dname':
					if record['domain'] not in cname_list:
						yield record['domain'] + ' IN DNAME ' + record['target']
				if record['type'] == 'ns':
					if record['domain'] not in cname_list:
						yield record['domain'] + ' IN NS ' + record['target']
				if record['type'] == 'txt':
					if record['domain'] not in cname_list:
						yield record['domain'] + ' IN TXT "' + record['target']+'"'

def main():
	try:
		config = ConfigParser.ConfigParser()
		config.read("nmczone.conf")
		json_rpc = config.get('nmczone', 'json_rpc')
		zonefile = config.get('nmczone', 'zonefile')
		block_count = config.get('nmczone', 'block_count')
		serial_multiplier = config.get('nmczone', 'serial_multiplier')
	except:
		print("Invalid config file.")
		exit()

	names_data = get_names(json_rpc)

	with open("zone-template.conf", 'r') as f:
		template = f.read()

	generate_zone(names_data['names'])

	with open(zonefile, 'w') as f:
		serial = str(names_data['block']*int(serial_multiplier))
		f.write(template.replace('%%serial%%', serial))
		for record in generate_zone(names_data['names']):
			f.write('\n'+record.encode('utf8'))
		f.write('\n')

	with open(block_count, 'w') as f:
		f.write(str(names_data['block']))


if __name__ == '__main__':
	main()