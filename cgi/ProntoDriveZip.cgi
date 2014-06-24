#!/usr/bin/perl
#
#  Copyright 2014 Anton Katsarov <anton@webface.bg>
#
#  Distributed under the MIT License.
#
#  See accompanying file COPYING or copy at
#  http://opensource.org/licenses/MIT
#
#
#
#  Descrition:
#
#  Serves a ZIP stream/archive of the shared files
#

use strict;
use warnings;

# Package Defs

package LocalCLI;
use IO::Socket::INET;

$CGP::TIMEOUT = 60*5-5;		# 5 minutes timeout

$CGP::ERR_STRING = "No error";

$CGP::CLI_CODE_OK = 200;
$CGP::CLI_CODE_OK_INLINE = 201;

sub connect {
  my ($this) = @_;
  $this->{isConnected}=0;

  delete $this->{theSocket} if(exists($this->{theSocket}));

  $this->{theSocket} = new IO::Socket::INET( %{$this->{connParams}} );

  unless (defined $this->{theSocket} && $this->{theSocket}) {
    $CGP::ERR_STRING="Can't open connection to CGPro Server";
    return undef;
  }
  ;
  $this->{theSocket}->autoflush(1);

  unless($this->_parseResponse()) {
    $CGP::ERR_STRING="Can't read CGPro Server prompt";
    return undef;
  }

  $this->send('AUTH SESSIONID '.$this->{login}.' '.$this->{sid});
  $this->_parseResponse();

  unless($this->isSuccess) {
    $CGP::ERR_STRING=$this->{errMsg};
    close($this->{theSocket});
    return undef;
  }
  $this->send('INLINE');
  $this->_parseResponse();
  $this->setStringsTranslateMode(0);
  $this->{isConnected} = 1;
  1;
}


sub new {
  my ($class, $params) = @_;
  my $this = {};

  $this->{login} = delete $params->{'login'};
  $this->{sid} = delete $params->{'sid'};

  $this->{isSecureLogin} = delete $params->{'SecureLogin'};
  $this->{isWebUserLogin} = delete $params->{'WebUserLogin'};


  die 'You must pass login parameter to CGP::CLI::new'
    unless defined $this->{login};
  die 'You must pass sid parameter to CGP::CLI::new'
    unless defined $this->{sid};

  die 'SecureLogin and WebUserLogin are mutually exclusive'
    if ($this->{isSecureLogin} && $this->{isWebUserLogin});

  #print %$params;
  bless $this, $class;
  $this->{connParams}=$params;

  if (!(defined $params->{'connectNow'}) || $params->{'connectNow'}) {
    unless($this->connect()) {
      return undef;
    }
  }
  return $this;
}

sub DESTROY {
  my $this = shift;
  $this->Logout() if ($this->{isConnected});
}

sub getErrCode {
  my $this = shift;
  return $this->{errCode};
}

sub getErrMessage {
  my $this = shift;
  return $this->{errMsg};
}

sub getErrCommand {
  my $this = shift;
  return $this->{'currentCGateCommand'};
}

sub isSuccess {
  my $this = shift;
  return ($this->{errCode} == $CGP::CLI_CODE_OK || $this->{errCode} == $CGP::CLI_CODE_OK_INLINE);
}

sub setStringsTranslateMode {
  my ($this, $onFlag) = @_;
  $this->{'translateStrings'} = $onFlag;
}

sub Logout {
  my $this = shift;
  if ($this->{isConnected}) {
    $this->send('QUIT');
    $this->_parseResponse();
    $this->{isConnected}=0;
  }
}

sub SendCommand {
  my ($this, $command) = @_;
  die 'usage CGP::CLI->SendCommand($commandString)'
    unless defined $command;
  $this->send($command);
  $this->_parseResponse();
}

sub GetResponseData {
  my ($this) = @_;
  $this->parseWords($this->getWords);
}

sub skipSpaces {
  my $this = shift;
  while($this->{'span'} < $this->{'len'} && substr($this->{'data'},$this->{'span'},1) =~ /\s/) { ++$this->{'span'}; }
}

sub readWord {
  my $this = shift;
  my ($isQuoted,$isBlock,$isUnkData)=(0,0,0);
  my $result="";

  $this->skipSpaces();
  if(substr($this->{'data'},$this->{'span'},1) eq '"') {
    $isQuoted=1; ++$this->{'span'};
  } elsif(substr($this->{'data'},$this->{'span'},1) eq '[') {
    $isBlock=1;
  } elsif(substr($this->{'data'},$this->{'span'},2) eq '#(') {
    $isUnkData=1;
    $result='#(';
    $this->{'span'}+=2;
  } elsif(substr($this->{'data'},$this->{'span'},3) eq '#I[') {
    #$isUnkData=1;
    $result='#I[';
    $this->{'span'}+=3;
  }
  while($this->{'span'} < $this->{'len'}) {
    my $ch=substr($this->{'data'},$this->{'span'},1);

    if($isQuoted) {
      if($ch eq '\\') {
        if(substr($this->{'data'},$this->{'span'}+1,3) =~ /^(?:\"|\\|\d\d\d)/) {
          $ch=substr($this->{'data'},++$this->{'span'},3);
          if($ch =~ /\d\d\d/) {
            $this->{'span'}+=2;
            $ch=chr($ch);
          } else {
            $ch=substr($ch,0,1);
            $ch='\\'.$ch unless($this->{'translateStrings'});
          }
        }
      } elsif($ch eq '"') {
        ++$this->{'span'};
        $this->skipSpaces();
        if(substr($this->{'data'},$this->{'span'},1) eq '"') {
          ++$this->{'span'};
        } else {
          last;
        }
      }
    } elsif($isBlock) {
      if($ch eq ']') {
        ++$this->{'span'};
        $this->skipSpaces();
        if(substr($this->{'data'},$this->{'span'},1) eq '[') {
          ++$this->{'span'};
        } else {
          $result .= ']';
          last;
        }

      }
    } elsif($isUnkData) {
      if($ch eq ')') {
        $result .= $ch;
        ++$this->{'span'};
        $this->skipSpaces();
        last;
      }
    } elsif($ch =~ /[-a-zA-Z0-9\x80-\xff_\.\@\!\#\%\]\:]/) {
    } else {
      last;
    }
    $result .= $ch;
    ++$this->{'span'};
  }
  return $result;
}


sub readKey() {
  my $this = shift;
  return $this->readWord();
}

sub readXML {
  my $this = shift;
  my $startSpan=$this->{'span'};
  for(;;) {
    $this->readXMLElem();
    if(substr($this->{'data'},$this->{'span'},1) ne '<') {
      last;
    } else {
      $this->{'span'}++;
    }
  }
  return substr($this->{'data'},$startSpan-1,$this->{'span'}-$startSpan+1);
}

sub readXMLElem {
  my $this = shift;

  my $element=undef;
  my $endPos=index($this->{'data'},'>',$this->{'span'});
  if($endPos<$this->{'span'}-1) {
    die "XML parsing error:",substr($this->{'data'},$this->{'span'}-1,100);
  }
  if(substr($this->{'data'},$endPos-1,1) eq '/') { # <tag attr="..." />
   $this->{'span'}=$endPos+1;
    return;
  }
  if(substr($this->{'data'},$this->{'span'},1)=~/[\!\?]/) { # <! or <?
   $this->{'span'}=$endPos+1;
    return;
  }
  unless(substr($this->{'data'},$this->{'span'},$endPos - $this->{'span'}+1) =~/(.+?)[ \>]/) {
    die "XML reading error:",substr($this->{'data'},$this->{'span'}-1,100);
  }
  $element=$1;
#print "endElement=$1\n";
  $this->{'span'}=$endPos+1;
#print "parsed=".substr($this->{'data'},$this->{'span'},10)."\n";
  $this->{'span'}++ while($this->{'span'} < $this->{'len'} && substr($this->{'data'},$this->{'span'},1) ne '<');
  while($this->{'span'} < $this->{'len'}) {
    if(substr($this->{'data'},$this->{'span'},$this->{'len'} - $this->{'span'})=~/^\<\/$element\>/) { #found closing element
      my $endPos=index($this->{'data'},'>',$this->{'span'}+1);
      $this->{'span'}=$endPos+1;
      return;
    }
    $this->{'span'}++;
    $this->readXMLElem();
  }
}

sub readValue() {
  my $this = shift;
  $this->skipSpaces();
  my $ch=substr($this->{'data'},$this->{'span'},1);
  if($ch eq '{') {
    ++$this->{'span'};
    return $this->readDictionary();
  } elsif($ch eq '(') {
    ++$this->{'span'};
    return $this->readArray();
  } elsif($ch eq '<') {
    ++$this->{'span'};
    return $this->readXML();
  } else {
    return $this->readWord();
  }
}

sub readArray() {
  my $this = shift;
  my $result=[];
  while($this->{'span'}<$this->{'len'}) {
    $this->skipSpaces();
    if(substr($this->{'data'},$this->{'span'},1) eq ')') {
      ++$this->{'span'};
      last;
    } else {
      my $theValue=$this->readValue();
      $this->skipSpaces();
      push(@$result,$theValue);
      if(substr($this->{'data'},$this->{'span'},1) eq ',') {
        ++$this->{'span'};
      } elsif(substr($this->{'data'},$this->{'span'},1) eq ')') {
      } else {
        die "CGPro output format error:",substr($this->{'data'},$this->{'span'},10);
      }
    }
  }
  return $result;
}

sub readDictionary {
  my $this = shift;
  my $result={};
  while($this->{'span'} < $this->{'len'}) {
    $this->skipSpaces();
    if(substr($this->{'data'},$this->{'span'},1) eq '}') {
      ++$this->{'span'};
      last;
    } else {
      my $theKey=$this->readKey();
      $this->skipSpaces();
      if(substr($this->{'data'},$this->{'span'},1) ne '=') { die "CGPro output format error:",substr($this->{'data'},$this->{'span'},10); }
      ++$this->{'span'};
      @$result{$theKey}=$this->readValue();
      $this->skipSpaces();
      if(substr($this->{'data'},$this->{'span'},1) ne ';') { die "CGPro output format error:",substr($this->{'data'},$this->{'span'},10); }
      ++$this->{'span'};
    }
  }
  return $result;
}

sub send {
  my ($this, $command) = @_;

  if (time()-$this->{'lastAccess'} > $CGP::TIMEOUT ||
      !($this->{theSocket}) ||
      $this->{theSocket}->error()) {
    $this->{theSocket}->shutdown('SHUT_RDWR') if($this->{theSocket});
    unless($this->connect()) {
      die "Failure: Can't reopen CLI connection";
    }
  }
  $this->{currentCGateCommand} = $command;
  print STDERR ref($this) . "->send($command)\n\n"
    if $this->{'debug'};
  $this->{'lastAccess'}=time();
  print {$this->{theSocket}} $command."\012";
}

sub parseWords {
  my $this = shift;
  $this->{'data'}=shift;
  $this->{'span'}=0;
  $this->{'len'}=length($this->{'data'});
  return $this->readValue();
}

sub getWords {
  my $this = shift;
  if ($this->{errCode} == $CGP::CLI_CODE_OK_INLINE) {
    return $this->{'inlineResponse'};
  }
  my ($bag, $line) = ('', '');
  my $firstLine = 1;
  my $lastLine = '';
  while (1) {
    $line = $this->{theSocket}->getline();
    chomp $line;
    $line = strip($line);
    if ($firstLine) {
      $line =~ /^(.)/;
      if ($1) {
        $lastLine = '\)' if $1 eq '(';
        $lastLine = '\}' if $1 eq '{';
        $lastLine = $lastLine . '$';
        $firstLine = 0;
      }
    }
    $bag .= $line;
    last if $line =~ /$lastLine/;
  }
  return $bag;
}

sub _parseResponse
  {
    my $this = shift;

    my $responseLine = $this->{theSocket}->getline();


    print STDERR "CGP::CLI->_parseResponse::responseLine = $responseLine\n\n"
      if $this->{'debug'};

    $responseLine =~ /^(\d+)\s(.*)$/;
    return $this->_setStrangeError($responseLine) unless ($1);
    $this->{errCode} = $1;
    if ($1 == $CGP::CLI_CODE_OK_INLINE) {
      $this->{'inlineResponse'} = $2;
      $this->{errMsg} = 'OK';
    } else {
      $this->{errMsg} = $2;
      chomp($this->{errMsg});
      $this->{errMsg} =~ s/\r$//;
    }
    $this->{'lastAccess'}=time();
    $this->isSuccess;
  }


# Account commands

sub GetAccountPrefs {
  my ($this, $account) = @_;
  die 'usage CGP::CLI->GetAccountPrefs($account)'
    unless defined $account;
  $this->send('GetAccountPrefs '.$account);
  return undef unless $this->_parseResponse();
  $this->parseWords($this->getWords);
}


# Main program

package main;

use CGI;
use IO::Compress::Zip 2.040 qw(:all);

my $q = new CGI();
my (undef, $account, $key, $sid) = split '/', $q->path_info();

my $cli = new LocalCLI( { PeerAddr => "127.0.0.1",
			  PeerPort => '106',
			  login => 'postmaster',
			  sid => $sid } );
unless($cli) {
  print "Content-type: text/plain\n\n";
  die "Can't login to CGPro: ".$CGP::ERR_STRING,"\n";
}

my $prefs =  $cli->GetAccountPrefs($account);


if (defined $prefs->{SharedFiles}->{$key}) {
  $prefs->{SharedFiles}->{$key}->{LastUpdated} =~ s/\D//g;
  my $expired = $prefs->{SharedFiles}->{$key}->{LastUpdated} + $prefs->{SharedFiles}->{$key}->{expires} - time();
  if ($expired > 0) {
    # print "Content-type: text/plain\n\n";
    my ($username, $domain) = split '@', $account;
    my $path = "/var/CommuniGate/Domains/$domain/$username.macnt/account.web/private";
    my @files = parseFiles(map {$_ = $path . $_;} @{$prefs->{SharedFiles}->{$key}->{file}});
    my $ext = substr $key, -8;
    print "Status: 200 OK\nContent-Disposition: attachment; filename=\"ProntoDrive-$ext.zip\"\nContent-Type: application/zip\nTransfer-Encoding: chunked\n\n";
    IO::Compress::Zip::zip ([@files] => '-',
			    FilterContainer => sub {
			      # Put some delay for performance reasons.
			      select(undef, undef, undef, 0.025);
			      # Chunk the output
			      my $length = length($_);
			      $_ = sprintf("%x", $length) . "\r\n" . $_ . "\r\n";
			      $_ .= "\r\n" unless $length;
			      1;
			    },
			    FilterName => sub { s[^$path/][] }
			   );
  } else {
    print "Content-type: text/plain\n\n";
    print "expired";
  }
} else {
  print "Content-type: text/plain\n\n";
  print "not found";
}
$cli->Logout();

sub parseFiles {
  my @files = @_;
  my @return;
  for my $file (@files) {
    if (-d $file) {
      my @listing;
      opendir(my $DIR, $file);
      while (my $filename = readdir $DIR) {
	next if $filename =~ m/(\.+|\.meta)$/;
	push @listing, $file . "/" . $filename;
      }
      closedir($DIR);
      push @return, parseFiles(@listing) if $listing[0];
    } else {
      push @return, $file;
    }
  }
  return @return;
}
